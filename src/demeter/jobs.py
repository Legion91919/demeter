"""The load job: land raw -> pick contract -> reconcile -> clean -> model, recording a job run.

Re-runnable: the same file (same bytes) can be loaded any number of times with the same result.
A file that fails reconciliation is quarantined and nothing from it reaches the model.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from demeter import contracts
from demeter.clean import clean
from demeter.config import Clock, Settings, utc_now
from demeter.contracts import LayoutError
from demeter.ingest import land
from demeter.model import Warehouse
from demeter.reconcile import reconcile

log = logging.getLogger("demeter.jobs")


def run_load(
    wh: Warehouse,
    settings: Settings,
    content: bytes,
    original_name: str,
    layout_id: str | None = None,
    clock: Clock = utc_now,
) -> dict[str, Any]:
    started_at = clock()
    t0 = time.perf_counter()
    job_run_id = str(uuid.uuid4())
    landed = land(settings.raw_dir, content, original_name, started_at)
    wh.register_raw_file(landed)
    wh.start_job_run(job_run_id, landed, started_at)
    run: dict[str, Any] = {
        "job_run_id": job_run_id,
        "file_id": landed.file_id,
        "rows_read": 0,
        "rows_written": 0,
        "rows_rejected": 0,
    }

    def finish(status: str, message: str, cur: Any = None) -> dict[str, Any]:
        run.update(
            status=status, message=message, finished_at=clock(), duration_ms=int((time.perf_counter() - t0) * 1000)
        )
        wh.finish_job_run(cur, run)
        log.info(
            "job_run %s file=%s status=%s read=%s written=%s rejected=%s ms=%s",
            job_run_id,
            landed.original_name,
            status,
            run["rows_read"],
            run["rows_written"],
            run["rows_rejected"],
            run["duration_ms"],
        )
        return run if cur is not None else (wh.job_run(job_run_id) or run)

    def quarantine(reason: str) -> dict[str, Any]:
        wh.quarantine_file(landed.file_id, job_run_id, reason, clock())
        run["rows_rejected"] = run["rows_read"]
        return finish("quarantined", reason)

    try:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return quarantine("file is not UTF-8 text")
        layout = contracts.resolve(text, layout_id)
        if layout is None:
            known = ", ".join(sorted(contracts.LAYOUTS))
            return quarantine(
                f"unknown layout '{layout_id}'"
                if layout_id
                else f"no single known layout matches this file's header (known: {known})"
            )
        run.update(layout_id=layout.id, borrower_id=layout.borrower_id)
        try:
            parsed = layout.split(text)
        except (LayoutError, ValueError) as exc:
            return quarantine(str(exc))
        run.update(as_of_date=parsed.as_of_date, rows_read=len(parsed.data_rows), total_unit=parsed.total_unit)

        result = reconcile(parsed, layout)
        run.update(stated_total=result.stated_total, computed_total=result.computed_total)
        if not result.ok:
            return quarantine(result.reason)
        if parsed.as_of_date is None:
            return quarantine("file has no readable as-of date")

        cleaned = clean(parsed, layout)
        with wh.transaction() as cur:
            run["rows_written"] = wh.load_facts(
                cur,
                layout_id=layout.id,
                borrower_id=layout.borrower_id,
                borrower_name=layout.borrower_name,
                as_of_date=parsed.as_of_date,
                rows=cleaned.rows,
                rejects=cleaned.rejects,
                file_id=landed.file_id,
                job_run_id=job_run_id,
                loaded_at=clock(),
            )
            run["rows_rejected"] = len(cleaned.rejects)
            message = "reconciled and loaded"
            if cleaned.rejects:
                message += f"; {len(cleaned.rejects)} row(s) quarantined"
            finish("succeeded", message, cur)
        return wh.job_run(job_run_id) or run
    except Exception as exc:  # the job run must always be closed, whatever went wrong
        log.exception("job_run %s failed", job_run_id)
        run["rows_written"] = 0
        return finish("failed", f"{type(exc).__name__}: {exc}")
