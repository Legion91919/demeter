"""Layout B: Marlowe Bay Properties (invented borrower).

Marlowe Bay Properties - Rent Schedule
Statement date: dd/mm/yyyy
Building,Suite,Lessee,Commencement,Expiry,"Rent p/m",Occupied (Y/N)
- day-first dates (dd/mm/yyyy), grouped amounts ("12,800.00"), occupancy Y / N
- no property codes: the building name is slugged into one
- last row: Building = Grand Total, Suite = "<n> units", Rent p/m = stated monthly total
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import (
    CanonicalRow,
    Layout,
    LayoutError,
    ParsedFile,
    SourceRow,
    lenient_amount,
    parse_amount,
    parse_date,
    slug,
)

DATE_FORMAT = "%d/%m/%Y"
STATEMENT = re.compile(r"^\s*Statement date:\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
UNITS = re.compile(r"(\d+)\s*units?", re.IGNORECASE)


class MarloweRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    building: str = Field(alias="Building", min_length=1)
    suite: str = Field(alias="Suite", min_length=1)
    lessee: str = Field(alias="Lessee", default="")
    commencement: date | None = Field(alias="Commencement")
    expiry: date | None = Field(alias="Expiry")
    rent_pm: Decimal = Field(alias="Rent p/m")
    occupied: Literal["Y", "N"] = Field(alias="Occupied (Y/N)")

    @field_validator("commencement", "expiry", mode="before")
    @classmethod
    def _date(cls, v: str) -> date | None:
        return parse_date(v, DATE_FORMAT)

    @field_validator("rent_pm", mode="before")
    @classmethod
    def _amount(cls, v: str) -> Decimal:
        return parse_amount(v)

    @field_validator("occupied", mode="before")
    @classmethod
    def _flag(cls, v: str) -> str:
        return v.strip().upper()


class MarloweLayout(Layout):
    id = "marlowe"
    borrower_id = "marlowe-bay"
    borrower_name = "Marlowe Bay Properties"
    header = ("Building", "Suite", "Lessee", "Commencement", "Expiry", "Rent p/m", "Occupied (Y/N)")
    row_model = MarloweRow

    def preamble_as_of(self, preamble: list[str]) -> date | None:
        for line in preamble:
            match = STATEMENT.match(line)
            if match:
                return parse_date(match.group(1), DATE_FORMAT)
        raise LayoutError("statement date line not found above the header")

    def is_total(self, row: SourceRow) -> bool:
        return row.values["Building"].strip().lower() == "grand total"

    def read_total(self, row: SourceRow) -> tuple[Decimal | None, int | None]:
        match = UNITS.search(row.values["Suite"])
        return lenient_amount(row.values["Rent p/m"]), int(match.group(1)) if match else None

    def amount_of(self, row: SourceRow) -> Decimal | None:
        return lenient_amount(row.values["Rent p/m"])

    def map_row(self, typed: BaseModel, parsed: ParsedFile) -> CanonicalRow:
        assert isinstance(typed, MarloweRow)
        if parsed.as_of_date is None:
            raise ValueError("file has no statement date")
        return CanonicalRow(
            borrower_id=self.borrower_id,
            property_code=slug(typed.building),
            property_name=typed.building,
            unit_ref=typed.suite,
            as_of_date=parsed.as_of_date,
            occupied=typed.occupied == "Y",
            monthly_rent=typed.rent_pm,
            lease_start=typed.commencement,
            lease_end=typed.expiry,
        )
