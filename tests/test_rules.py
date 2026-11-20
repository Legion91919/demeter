"""Unit tests for the clean and reconcile rules, using small hand-made files."""

from __future__ import annotations

from rentroll.clean import clean
from rentroll.contracts import LAYOUTS
from rentroll.reconcile import reconcile

HEADER = "property_code,property_name,unit_no,tenant,lease_start,lease_end,monthly_rent,status,roll_date\n"
KR = LAYOUTS["keelridge"]


def run(body: str):
    parsed = KR.split(HEADER + body)
    return parsed, reconcile(parsed, KR), clean(parsed, KR)


def test_missing_total_row_fails_reconciliation():
    _, rec, _ = run("P1,One,1,T,2025-01-01,2026-12-31,100.00,OCCUPIED,2026-10-31\n")
    assert not rec.ok and "no total row" in rec.reason


def test_unreadable_amount_fails_reconciliation():
    _, rec, _ = run("P1,One,1,T,2025-01-01,2026-12-31,abc,OCCUPIED,2026-10-31\nTOTAL,,,,,,100.00,,\n")
    assert not rec.ok and "unreadable on line(s) 2" in rec.reason


def test_unit_count_mismatch_fails_reconciliation():
    marlowe = LAYOUTS["marlowe"]
    text = (
        'Statement date: 31/10/2026\nBuilding,Suite,Lessee,Commencement,Expiry,"Rent p/m",Occupied (Y/N)\n'
        'B,1,T,01/01/2025,01/01/2027,"100.00",Y\nGrand Total,2 units,,,,"100.00",\n'
    )
    parsed = marlowe.split(text)
    rec = reconcile(parsed, marlowe)
    assert not rec.ok and "1 unit rows but the total row states 2" in rec.reason


def test_row_rules_reject_with_reasons():
    body = (
        "P1,One,1,T,2025-01-01,2024-12-31,100.00,OCCUPIED,2026-10-31\n"  # ends before it starts
        "P1,One,2,,,,0.00,OCCUPIED,2026-10-31\n"  # occupied, no rent
        "P1,One,3,,,,50.00,VACANT,2026-10-31\n"  # vacant with rent
        "P1,One,4,T,2025-01-01,2027-01-01,10.00,OCCUPIED,2026-09-30\n"  # different roll date
        "P1,One,5,T,2025-01-01,2027-01-01,10.00,OCCUPIED,2026-10-31\n"
        "P1,One,5,T,2025-01-01,2027-01-01,10.00,OCCUPIED,2026-10-31\n"  # duplicate
        "P1,One,6,T,31/01/2025,2027-01-01,10.00,LET,2026-10-31\n"  # bad date and status
        "TOTAL,,,,,,190.00,,\n"
    )
    _, rec, result = run(body)
    assert rec.ok
    reasons = {r.line_no: r.reason for r in result.rejects}
    assert "lease ends before it starts" in reasons[2]
    assert "occupied unit has no rent" in reasons[3]
    assert "vacant unit has rent" in reasons[4]
    assert "differs from the file's 2026-10-31" in reasons[5]
    assert "duplicate unit 5 (first on line 6)" in reasons[7]
    assert "lease_start" in reasons[8] and "status" in reasons[8]
    assert [r.unit_ref for _, r in result.rows] == ["5"]
