"""Contract tests: each borrower layout on its sample file (runs in CI on every push)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from conftest import KEELRIDGE, MARLOWE, TIDEWATER, TIDEWATER_BAD
from rentroll import contracts
from rentroll.clean import clean
from rentroll.contracts.base import parse_amount
from rentroll.reconcile import reconcile


def parse(path):
    text = path.read_text(encoding="utf-8")
    layout = contracts.resolve(text)
    assert layout is not None, f"no layout detected for {path.name}"
    return layout, layout.split(text)


@pytest.mark.parametrize(
    ("path", "layout_id", "rows", "stated", "units", "as_of"),
    [
        (KEELRIDGE, "keelridge", 8, Decimal("164515.75"), None, date(2026, 10, 31)),
        (MARLOWE, "marlowe", 9, Decimal("110275.00"), 9, date(2026, 10, 31)),
        (TIDEWATER, "tidewater", 6, Decimal("1412300.00"), None, date(2026, 10, 31)),
    ],
)
def test_layout_detects_splits_and_reconciles_its_sample(path, layout_id, rows, stated, units, as_of):
    layout, parsed = parse(path)
    assert layout.id == layout_id
    assert len(parsed.data_rows) == rows
    assert parsed.stated_total == stated
    assert parsed.stated_units == units
    assert parsed.as_of_date == as_of
    assert reconcile(parsed, layout).ok


def test_keelridge_maps_iso_dates_status_and_property_codes():
    layout, parsed = parse(KEELRIDGE)
    result = clean(parsed, layout)
    assert not result.rejects
    source, first = result.rows[0]
    assert source.line_no == 2
    assert (first.property_code, first.unit_ref, first.monthly_rent) == ("KR-01", "101", Decimal("18450.00"))
    assert first.lease_start == date(2024, 3, 1) and first.occupied
    vacant = [r for _, r in result.rows if not r.occupied]
    assert [v.unit_ref for v in vacant] == ["104", "3A"]


def test_marlowe_reads_preamble_day_first_dates_grouped_amounts_and_quarantines_bad_suite():
    layout, parsed = parse(MARLOWE)
    result = clean(parsed, layout)
    assert len(result.rows) == 8
    assert [(r.line_no, r.reason) for r in result.rejects] == [(8, "Suite: String should have at least 1 character")]
    _, g01 = result.rows[0]
    assert g01.property_code == "harbour-lofts" and g01.property_name == "Harbour Lofts"
    assert g01.lease_start == date(2025, 2, 1) and g01.lease_end == date(2028, 1, 31)
    assert g01.monthly_rent == Decimal("12800.00")


def test_tidewater_converts_annual_rent_to_monthly_and_inverts_vacant_flag():
    layout, parsed = parse(TIDEWATER)
    assert parsed.total_unit == "annual rent"
    result = clean(parsed, layout)
    by_unit = {r.unit_ref: r for _, r in result.rows}
    assert by_unit["A1"].monthly_rent == Decimal("16500.00")
    assert by_unit["A1"].occupied and not by_unit["A3"].occupied
    assert by_unit["1"].lease_end == date(2028, 9, 30)


def test_broken_sample_does_not_reconcile_and_says_why():
    layout, parsed = parse(TIDEWATER_BAD)
    result = reconcile(parsed, layout)
    assert not result.ok
    assert "1,412,300.00" in result.reason and "1,408,300.00" in result.reason
    assert "+4,000.00" in result.reason


def test_unknown_header_matches_no_layout():
    assert contracts.resolve("a,b,c\n1,2,3\n") is None


@pytest.mark.parametrize(("text", "expected"), [("12,800.00", Decimal("12800.00")), (" 7 ", Decimal("7.00"))])
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "NaN"])
def test_parse_amount_rejects_non_money(text):
    with pytest.raises(ValueError):
        parse_amount(text)
