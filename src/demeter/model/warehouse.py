"""The DuckDB warehouse: raw file register, job runs, quarantine, dimensions and the rent-roll fact.

All writes for one load happen in one transaction, so a file is either fully loaded or not at all.
Facts are upserted on their natural key (borrower, property, unit, as-of date): re-running a load
never duplicates rows.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import duckdb

from demeter.clean import Reject
from demeter.contracts import CanonicalRow, SourceRow
from demeter.ingest import LandedFile

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_files (
    file_id VARCHAR PRIMARY KEY, original_name VARCHAR NOT NULL, size_bytes BIGINT NOT NULL,
    received_at TIMESTAMP NOT NULL, layout_id VARCHAR, status VARCHAR NOT NULL);
CREATE TABLE IF NOT EXISTS job_runs (
    job_run_id VARCHAR PRIMARY KEY, file_id VARCHAR NOT NULL, original_name VARCHAR NOT NULL,
    layout_id VARCHAR, borrower_id VARCHAR, as_of_date DATE,
    started_at TIMESTAMP NOT NULL, finished_at TIMESTAMP, duration_ms INTEGER,
    status VARCHAR NOT NULL, rows_read INTEGER DEFAULT 0, rows_written INTEGER DEFAULT 0,
    rows_rejected INTEGER DEFAULT 0, stated_total DECIMAL(18,2), computed_total DECIMAL(18,2),
    total_unit VARCHAR, message VARCHAR);
CREATE TABLE IF NOT EXISTS quarantine_files (
    file_id VARCHAR NOT NULL, job_run_id VARCHAR NOT NULL, reason VARCHAR NOT NULL,
    quarantined_at TIMESTAMP NOT NULL, PRIMARY KEY (file_id, job_run_id));
CREATE TABLE IF NOT EXISTS quarantine_rows (
    file_id VARCHAR NOT NULL, source_row INTEGER NOT NULL, job_run_id VARCHAR NOT NULL,
    reason VARCHAR NOT NULL, raw_line VARCHAR NOT NULL, PRIMARY KEY (file_id, source_row));
CREATE TABLE IF NOT EXISTS dim_borrower (
    borrower_id VARCHAR PRIMARY KEY, borrower_name VARCHAR NOT NULL, layout_id VARCHAR NOT NULL);
CREATE TABLE IF NOT EXISTS dim_property (
    borrower_id VARCHAR NOT NULL, property_code VARCHAR NOT NULL, property_name VARCHAR NOT NULL,
    PRIMARY KEY (borrower_id, property_code));
CREATE TABLE IF NOT EXISTS fact_unit_rent (
    borrower_id VARCHAR NOT NULL, property_code VARCHAR NOT NULL, unit_ref VARCHAR NOT NULL,
    as_of_date DATE NOT NULL, occupied BOOLEAN NOT NULL, monthly_rent DECIMAL(18,2) NOT NULL,
    lease_start DATE, lease_end DATE,
    source_file_id VARCHAR NOT NULL, source_row INTEGER NOT NULL, job_run_id VARCHAR NOT NULL,
    loaded_at TIMESTAMP NOT NULL,
    PRIMARY KEY (borrower_id, property_code, unit_ref, as_of_date));
"""

JOB_RUN_COLUMNS = (
    "job_run_id",
    "file_id",
    "original_name",
    "layout_id",
    "borrower_id",
    "as_of_date",
    "started_at",
    "finished_at",
    "duration_ms",
    "status",
    "rows_read",
    "rows_written",
    "rows_rejected",
    "stated_total",
    "computed_total",
    "total_unit",
    "message",
)
UPDATABLE = tuple(c for c in JOB_RUN_COLUMNS if c not in {"job_run_id", "file_id", "original_name", "started_at"})


def _rows(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    names = [d[0] for d in cursor.description or []]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


class Warehouse:
    def __init__(self, path: Path | str) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(path))
        self._lock = threading.RLock()
        self._conn.execute(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def _cursor(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with self._lock:
            cur = self._conn.cursor()
            try:
                yield cur
            finally:
                cur.close()

    @contextmanager
    def transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with self._cursor() as cur:
            cur.execute("BEGIN TRANSACTION")
            try:
                yield cur
                cur.execute("COMMIT")
            except BaseException:
                cur.execute("ROLLBACK")
                raise

    def ping(self) -> bool:
        with self._cursor() as cur:
            return cur.execute("SELECT 1").fetchone() == (1,)

    # ---- raw + job runs ----------------------------------------------------------------
    def register_raw_file(self, landed: LandedFile) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO raw_files VALUES (?, ?, ?, ?, NULL, 'landed') ON CONFLICT (file_id) DO NOTHING",
                [landed.file_id, landed.original_name, landed.size_bytes, landed.received_at],
            )

    def start_job_run(self, job_run_id: str, landed: LandedFile, started_at: datetime) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO job_runs (job_run_id, file_id, original_name, started_at, status) "
                "VALUES (?, ?, ?, ?, 'running')",
                [job_run_id, landed.file_id, landed.original_name, started_at],
            )

    def finish_job_run(self, cur: duckdb.DuckDBPyConnection | None, run: dict[str, Any]) -> None:
        """Write the final job-run record (inside the load transaction when one is given)."""
        sets = ", ".join(f"{c} = ?" for c in UPDATABLE)
        params = [run.get(c) for c in UPDATABLE] + [run["job_run_id"]]
        sql = f"UPDATE job_runs SET {sets} WHERE job_run_id = ?"
        file_status = {"succeeded": "loaded", "quarantined": "quarantined"}.get(run["status"], "failed")
        file_sql = "UPDATE raw_files SET status = ?, layout_id = coalesce(?, layout_id) WHERE file_id = ?"
        file_params = [file_status, run.get("layout_id"), run["file_id"]]
        if cur is not None:
            cur.execute(sql, params)
            cur.execute(file_sql, file_params)
            return
        with self._cursor() as own:
            own.execute(sql, params)
            own.execute(file_sql, file_params)

    def quarantine_file(self, file_id: str, job_run_id: str, reason: str, at: datetime) -> None:
        with self._cursor() as cur:
            cur.execute("INSERT INTO quarantine_files VALUES (?, ?, ?, ?)", [file_id, job_run_id, reason, at])

    # ---- the load itself ---------------------------------------------------------------
    def load_facts(
        self,
        cur: duckdb.DuckDBPyConnection,
        *,
        layout_id: str,
        borrower_id: str,
        borrower_name: str,
        as_of_date: date,
        rows: list[tuple[SourceRow, CanonicalRow]],
        rejects: list[Reject],
        file_id: str,
        job_run_id: str,
        loaded_at: datetime,
    ) -> int:
        """Upsert dimensions and facts, replace the partition's leftovers, record row rejects."""
        cur.execute(
            "INSERT INTO dim_borrower VALUES (?, ?, ?) ON CONFLICT (borrower_id) DO UPDATE SET "
            "borrower_name = excluded.borrower_name, layout_id = excluded.layout_id",
            [borrower_id, borrower_name, layout_id],
        )
        properties = {(r.borrower_id, r.property_code): r.property_name for _, r in rows}
        for (b, code), name in properties.items():
            cur.execute(
                "INSERT INTO dim_property VALUES (?, ?, ?) ON CONFLICT (borrower_id, property_code) "
                "DO UPDATE SET property_name = excluded.property_name",
                [b, code, name],
            )
        for source, r in rows:
            cur.execute(
                "INSERT INTO fact_unit_rent VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (borrower_id, property_code, unit_ref, as_of_date) DO UPDATE SET "
                "occupied = excluded.occupied, monthly_rent = excluded.monthly_rent, "
                "lease_start = excluded.lease_start, lease_end = excluded.lease_end, "
                "source_file_id = excluded.source_file_id, source_row = excluded.source_row, "
                "job_run_id = excluded.job_run_id, loaded_at = excluded.loaded_at",
                [
                    r.borrower_id,
                    r.property_code,
                    r.unit_ref,
                    r.as_of_date,
                    r.occupied,
                    r.monthly_rent,
                    r.lease_start,
                    r.lease_end,
                    file_id,
                    source.line_no,
                    job_run_id,
                    loaded_at,
                ],
            )
        # A corrected file for the same borrower and month replaces the previous one completely:
        # units no longer on the roll must not linger.
        cur.execute(
            "DELETE FROM fact_unit_rent WHERE borrower_id = ? AND as_of_date = ? AND job_run_id <> ?",
            [borrower_id, as_of_date, job_run_id],
        )
        for rej in rejects:
            cur.execute(
                "INSERT INTO quarantine_rows VALUES (?, ?, ?, ?, ?) ON CONFLICT (file_id, source_row) "
                "DO UPDATE SET job_run_id = excluded.job_run_id, reason = excluded.reason",
                [file_id, rej.line_no, job_run_id, rej.reason, rej.raw],
            )
        return len(rows)

    # ---- reads -------------------------------------------------------------------------
    def job_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute(
                f"SELECT {', '.join(JOB_RUN_COLUMNS)} FROM job_runs ORDER BY started_at DESC, job_run_id DESC LIMIT ?",
                [limit],
            )
            return _rows(cur)

    def job_run(self, job_run_id: str) -> dict[str, Any] | None:
        with self._cursor() as cur:
            cur.execute(f"SELECT {', '.join(JOB_RUN_COLUMNS)} FROM job_runs WHERE job_run_id = ?", [job_run_id])
            found = _rows(cur)
            return found[0] if found else None

    def count(self, table: str) -> int:
        if table not in {
            "fact_unit_rent",
            "job_runs",
            "quarantine_files",
            "quarantine_rows",
            "raw_files",
            "dim_property",
            "dim_borrower",
        }:
            raise ValueError(table)
        with self._cursor() as cur:
            row = cur.execute(f"SELECT count(*) FROM {table}").fetchone()
            return int(row[0]) if row else 0

    def portfolio(self) -> list[dict[str, Any]]:
        """Occupancy and contracted monthly rent per property, from each borrower's latest roll."""
        with self._cursor() as cur:
            cur.execute(
                """
                WITH latest AS (
                    SELECT borrower_id, max(as_of_date) AS as_of_date FROM fact_unit_rent GROUP BY borrower_id)
                SELECT f.borrower_id, b.borrower_name, f.property_code, p.property_name, f.as_of_date,
                       count(*) AS units,
                       count(*) FILTER (WHERE f.occupied) AS occupied_units,
                       sum(f.monthly_rent) AS monthly_rent,
                       max(f.loaded_at) AS loaded_at,
                       any_value(f.source_file_id) AS source_file_id,
                       any_value(r.original_name) AS source_file_name,
                       any_value(f.job_run_id) AS job_run_id
                FROM fact_unit_rent f
                JOIN latest l USING (borrower_id, as_of_date)
                JOIN dim_borrower b USING (borrower_id)
                JOIN dim_property p USING (borrower_id, property_code)
                JOIN raw_files r ON r.file_id = f.source_file_id
                GROUP BY ALL
                ORDER BY b.borrower_name, p.property_name
                """
            )
            rows = _rows(cur)
        for row in rows:
            row["occupancy_pct"] = (Decimal(100) * row["occupied_units"] / row["units"]).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        return rows

    def freshness(self) -> dict[str, Any]:
        with self._cursor() as cur:
            last_load = cur.execute("SELECT max(finished_at) FROM job_runs WHERE status = 'succeeded'").fetchone()
            as_of = cur.execute("SELECT max(as_of_date) FROM fact_unit_rent").fetchone()
            quarantined = cur.execute("SELECT count(*) FROM raw_files WHERE status = 'quarantined'").fetchone()
        return {
            "last_successful_load_at": last_load[0] if last_load else None,
            "latest_as_of_date": as_of[0] if as_of else None,
            "files_in_quarantine": int(quarantined[0]) if quarantined else 0,
        }

    def property_lineage(self, borrower_id: str, property_code: str) -> list[dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute(
                """
                WITH latest AS (SELECT max(as_of_date) AS d FROM fact_unit_rent WHERE borrower_id = ?)
                SELECT f.unit_ref, f.occupied, f.monthly_rent, f.as_of_date, f.lease_start, f.lease_end,
                       f.source_file_id, r.original_name AS source_file_name, r.received_at,
                       f.source_row, f.job_run_id, f.loaded_at
                FROM fact_unit_rent f JOIN latest ON f.as_of_date = latest.d
                JOIN raw_files r ON r.file_id = f.source_file_id
                WHERE f.borrower_id = ? AND f.property_code = ?
                ORDER BY f.source_row
                """,
                [borrower_id, borrower_id, property_code],
            )
            return _rows(cur)

    def property(self, borrower_id: str, property_code: str) -> dict[str, Any] | None:
        with self._cursor() as cur:
            cur.execute(
                "SELECT p.borrower_id, b.borrower_name, p.property_code, p.property_name FROM dim_property p "
                "JOIN dim_borrower b USING (borrower_id) WHERE p.borrower_id = ? AND p.property_code = ?",
                [borrower_id, property_code],
            )
            found = _rows(cur)
            return found[0] if found else None

    def quarantine(self) -> dict[str, list[dict[str, Any]]]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT q.file_id, r.original_name, q.job_run_id, q.reason, q.quarantined_at FROM quarantine_files q "
                "JOIN raw_files r USING (file_id) ORDER BY q.quarantined_at DESC"
            )
            files = _rows(cur)
            cur.execute(
                "SELECT q.file_id, r.original_name, q.source_row, q.job_run_id, q.reason FROM quarantine_rows q "
                "JOIN raw_files r USING (file_id) ORDER BY r.original_name, q.source_row"
            )
            rows = _rows(cur)
        return {"files": files, "rows": rows}
