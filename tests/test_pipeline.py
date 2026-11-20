"""Acceptance tests for slice 1 at the job level (one per criterion), plus job-run bookkeeping."""

from __future__ import annotations

import hashlib
from decimal import Decimal

from conftest import KEELRIDGE, MARLOWE, TIDEWATER, TIDEWATER_BAD, VALID
from demeter.jobs import run_load
from demeter.lineage import property_lineage


def load(wh, settings, clock, path, layout=None):
    return run_load(wh, settings, path.read_bytes(), path.name, layout, clock)


# AC1: Given a valid file, when it is loaded twice, then the warehouse has no duplicates
def test_ac1_loading_the_same_file_twice_creates_no_duplicates(wh, settings, clock):
    first = load(wh, settings, clock, KEELRIDGE)
    facts_after_first = wh.count("fact_unit_rent")
    second = load(wh, settings, clock, KEELRIDGE)
    assert first["status"] == second["status"] == "succeeded"
    assert facts_after_first == wh.count("fact_unit_rent") == 8
    assert wh.count("raw_files") == 1  # same bytes, same checksum, landed once
    assert wh.count("job_runs") == 2  # but every run is recorded
    assert second["rows_written"] == 8 and second["job_run_id"] != first["job_run_id"]


def test_ac1_rejected_rows_are_not_duplicated_on_reload(wh, settings, clock):
    load(wh, settings, clock, MARLOWE)
    load(wh, settings, clock, MARLOWE)
    assert wh.count("quarantine_rows") == 1
    assert wh.count("fact_unit_rent") == 8


def test_corrected_file_for_same_month_replaces_the_previous_one(wh, settings, clock):
    load(wh, settings, clock, KEELRIDGE)
    text = KEELRIDGE.read_text()
    lines = [ln for ln in text.splitlines() if not ln.startswith("KR-02,Anchor Point Offices,3B")]
    lines[-1] = "TOTAL,,,,,,136875.50,,"
    corrected = ("\n".join(lines) + "\n").encode()
    run = run_load(wh, settings, corrected, "keelridge-estates_2026-10_corrected.csv", None, clock)
    assert run["status"] == "succeeded", run["message"]
    assert wh.count("fact_unit_rent") == 7


# AC2: Given a file whose total doesn't match its rows, the load fails and the file is quarantined with a reason
def test_ac2_total_mismatch_fails_the_load_and_quarantines_the_file(wh, settings, clock):
    run = load(wh, settings, clock, TIDEWATER_BAD)
    assert run["status"] == "quarantined"
    assert "difference +4,000.00" in run["message"]
    assert run["rows_read"] == 6 and run["rows_written"] == 0 and run["rows_rejected"] == 6
    assert wh.count("fact_unit_rent") == 0  # never half-loaded
    q = wh.quarantine()["files"]
    assert len(q) == 1 and q[0]["original_name"] == TIDEWATER_BAD.name and "states 1,408,300.00" in q[0]["reason"]


def test_ac2_quarantined_file_is_kept_unchanged_with_its_checksum(wh, settings, clock):
    content = TIDEWATER_BAD.read_bytes()
    run = load(wh, settings, clock, TIDEWATER_BAD)
    stored = settings.raw_dir / f"{run['file_id']}.csv"
    assert stored.read_bytes() == content
    assert run["file_id"] == hashlib.sha256(content).hexdigest()


def test_ac2_bad_file_does_not_disturb_already_loaded_data(wh, settings, clock):
    load(wh, settings, clock, TIDEWATER)
    before = wh.portfolio()
    load(wh, settings, clock, TIDEWATER_BAD)
    assert wh.portfolio() == before


def test_unknown_layout_and_non_utf8_files_are_quarantined(wh, settings, clock):
    assert run_load(wh, settings, b"a,b\n1,2\n", "odd.csv", None, clock)["status"] == "quarantined"
    assert run_load(wh, settings, b"\xff\xfe\x00bad", "bin.csv", None, clock)["message"] == "file is not UTF-8 text"
    named = run_load(wh, settings, KEELRIDGE.read_bytes(), KEELRIDGE.name, "nope", clock)
    assert named["message"] == "unknown layout 'nope'"


# AC3: Given a dashboard figure, then its source file and row can be looked up
def test_ac3_every_unit_behind_a_property_figure_traces_to_file_row_and_job_run(wh, settings, clock):
    run = load(wh, settings, clock, KEELRIDGE)
    found = property_lineage(wh, settings.raw_dir, "keelridge-estates", "KR-02")
    assert found is not None and found["property_name"] == "Anchor Point Offices"
    assert [r["source_row"] for r in found["rows"]] == [6, 7, 8, 9]
    lines = KEELRIDGE.read_text().splitlines()
    for row in found["rows"]:
        assert row["source_file_id"] == run["file_id"]
        assert row["source_file_name"] == KEELRIDGE.name
        assert row["job_run_id"] == run["job_run_id"]
        assert row["raw_line"] == lines[row["source_row"] - 1]
    figure = next(p for p in wh.portfolio() if p["property_code"] == "KR-02")
    assert sum(r["monthly_rent"] for r in found["rows"]) == figure["monthly_rent"]


def test_job_runs_record_counts_duration_and_status(wh, settings, clock):
    for path in [*VALID, TIDEWATER_BAD]:
        load(wh, settings, clock, path)
    runs = {r["original_name"]: r for r in wh.job_runs()}
    m = runs[MARLOWE.name]
    assert (m["status"], m["rows_read"], m["rows_written"], m["rows_rejected"]) == ("succeeded", 9, 8, 1)
    assert m["duration_ms"] >= 0 and m["finished_at"] > m["started_at"]
    assert m["stated_total"] == m["computed_total"] == Decimal("110275.00")
    assert runs[TIDEWATER_BAD.name]["status"] == "quarantined"


def test_portfolio_figures_equal_the_model_tables(wh, settings, clock):
    for path in VALID:
        load(wh, settings, clock, path)
    portfolio = {(p["borrower_id"], p["property_code"]): p for p in wh.portfolio()}
    assert len(portfolio) == 6
    quay = portfolio[("keelridge-estates", "KR-01")]
    assert (quay["units"], quay["occupied_units"], quay["occupancy_pct"]) == (4, 3, Decimal("75.0"))
    assert quay["monthly_rent"] == Decimal("54725.50")
    mews = portfolio[("tidewater-living", "TW7")]
    assert mews["monthly_rent"] == Decimal("43650.00")  # (198000 + 171600 + 154200) / 12
    lofts = portfolio[("marlowe-bay", "harbour-lofts")]
    assert lofts["units"] == 4  # the suite-less row is quarantined, not counted
