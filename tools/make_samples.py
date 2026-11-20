#!/usr/bin/env python3
"""Generate the invented borrower rent rolls in samples/.

Every borrower, property, tenant and amount here is invented. Re-run to rebuild the samples:
    python3 tools/make_samples.py
Totals are computed, so the valid files always reconcile; the broken file is wrong on purpose.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "samples"


def money(value: Decimal) -> str:
    return f"{value:.2f}"


def money_grouped(value: Decimal) -> str:
    return f"{value:,.2f}"


def keelridge() -> str:
    # Layout A: ISO dates, plain amounts, roll date on every row, "TOTAL" row states rent only.
    units = [
        ("KR-01", "Keelridge Quay", "101", "Saltmarsh Bakery", "2024-03-01", "2027-02-28", "18450.00", "OCCUPIED"),
        ("KR-01", "Keelridge Quay", "102", "Pebble Lane Optometry", "2025-01-01", "2027-12-31", "15200.00", "OCCUPIED"),
        ("KR-01", "Keelridge Quay", "103", "Northlight Dental", "2023-07-01", "2026-06-30", "21075.50", "OCCUPIED"),
        ("KR-01", "Keelridge Quay", "104", "", "", "", "0.00", "VACANT"),
        ("KR-02", "Anchor Point Offices", "2A", "Fathom Analytics", "2024-09-01", "2029-08-31", "42300.00", "OCCUPIED"),
        ("KR-02", "Anchor Point Offices", "2B", "Brightwater Law", "2022-04-01", "2027-03-31", "39850.00", "OCCUPIED"),
        ("KR-02", "Anchor Point Offices", "3A", "", "", "", "0.00", "VACANT"),
        ("KR-02", "Anchor Point Offices", "3B", "Gullwing Travel", "2025-06-01", "2028-05-31", "27640.25", "OCCUPIED"),
    ]
    lines = ["property_code,property_name,unit_no,tenant,lease_start,lease_end,monthly_rent,status,roll_date"]
    total = Decimal("0")
    for u in units:
        lines.append(",".join(u) + ",2026-10-31")
        total += Decimal(u[6])
    lines.append(f"TOTAL,,,,,,{money(total)},,")
    return "\n".join(lines) + "\n"


def marlowe() -> str:
    # Layout B: two preamble lines, day-first dates, grouped amounts in quotes, Y/N occupancy,
    # "Grand Total" row states rent and unit count. One suite is missing its reference on purpose:
    # the row counts towards the borrower's total but is quarantined by the clean step.
    units = [
        ("Harbour Lofts", "G01", "Tern & Co Studio", "01/02/2025", "31/01/2028", "12800.00", "Y"),
        ("Harbour Lofts", "G02", "Driftwood Coffee", "15/08/2024", "14/08/2027", "9650.00", "Y"),
        ("Harbour Lofts", "101", "", "", "", "0.00", "N"),
        ("Harbour Lofts", "102", "Lanternfish Games", "01/11/2023", "31/10/2026", "11475.00", "Y"),
        ("Harbour Lofts", "", "Coastline Print Shop", "01/03/2025", "28/02/2027", "8200.00", "Y"),
        ("Ropewalk Yard", "U1", "Seabright Joinery", "01/05/2022", "30/04/2027", "31250.00", "Y"),
        ("Ropewalk Yard", "U2", "Mooring Line Logistics", "01/09/2025", "31/08/2030", "36900.00", "Y"),
        ("Ropewalk Yard", "U3", "", "", "", "0.00", "N"),
        ("Ropewalk Yard", "U4", "", "", "", "0.00", "N"),
    ]
    lines = [
        "Marlowe Bay Properties - Rent Schedule",
        "Statement date: 31/10/2026",
        'Building,Suite,Lessee,Commencement,Expiry,"Rent p/m",Occupied (Y/N)',
    ]
    total = Decimal("0")
    for b, s, lessee, start, end, rent, occ in units:
        lines.append(f'{b},{s},{lessee},{start},{end},"{money_grouped(Decimal(rent))}",{occ}')
        total += Decimal(rent)
    lines.append(f'Grand Total,{len(units)} units,,,,"{money_grouped(total)}",')
    return "\n".join(lines) + "\n"


TIDEWATER_UNITS = [
    ("TW7", "Tidewater Mews", "A1", "Kelp & Co Florist", "01-Jun-2025", "31-May-2027", "198000.00", "FALSE"),
    ("TW7", "Tidewater Mews", "A2", "Ebbtide Physio", "01-Jan-2024", "31-Dec-2026", "171600.00", "FALSE"),
    ("TW7", "Tidewater Mews", "A3", "", "", "", "0.00", "TRUE"),
    ("TW7", "Tidewater Mews", "B1", "Shoreline Tutors", "01-Mar-2026", "28-Feb-2029", "154200.00", "FALSE"),
    ("TW9", "Breakwater House", "1", "Cormorant Insurance Brokers", "01-Oct-2023", "30-Sep-2028", "486000.00", "FALSE"),
    ("TW9", "Breakwater House", "2", "Sandbar Architects", "01-Feb-2025", "31-Jan-2030", "402500.00", "FALSE"),
]


def tidewater(total_offset: Decimal = Decimal("0")) -> str:
    # Layout C: dd-Mon-yyyy dates, ANNUAL rent, a Vacant flag (TRUE/FALSE), period as yyyy-mm,
    # "TOTALS" sits in the PropName column and states annual rent.
    lines = ["PropID,PropName,UnitRef,Occupant,StartDate,EndDate,AnnualRent,Vacant,Period"]
    total = Decimal("0")
    for u in TIDEWATER_UNITS:
        lines.append(",".join(u) + ",2026-10")
        total += Decimal(u[6])
    lines.append(f",TOTALS,,,,,{money(total + total_offset)},,")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    files = {
        "keelridge-estates_2026-10.csv": keelridge(),
        "marlowe-bay_2026-10.csv": marlowe(),
        "tidewater-living_2026-10_v1-bad-total.csv": tidewater(Decimal("-4000.00")),
        "tidewater-living_2026-10_v2.csv": tidewater(),
    }
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8", newline="")
        print(f"wrote samples/{name}")


if __name__ == "__main__":
    main()
