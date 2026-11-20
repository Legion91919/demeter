"""Layout C: Tidewater Living (invented borrower).

PropID,PropName,UnitRef,Occupant,StartDate,EndDate,AnnualRent,Vacant,Period
- dd-Mon-yyyy dates, ANNUAL rent, Vacant flag TRUE / FALSE (inverted sense), period yyyy-mm
- as-of date is the last day of the period month
- last row: PropName = TOTALS, AnnualRent = stated ANNUAL total (reconciled in annual terms)
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import CENT, CanonicalRow, Layout, ParsedFile, SourceRow, lenient_amount, parse_amount, parse_date

DATE_FORMAT = "%d-%b-%Y"


def period_end(text: str) -> date:
    try:
        year, month = (int(p) for p in text.strip().split("-"))
        return date(year, month, calendar.monthrange(year, month)[1])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"period '{text}' is not in the form yyyy-mm") from exc


class TidewaterRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    prop_id: str = Field(alias="PropID", min_length=1)
    prop_name: str = Field(alias="PropName", min_length=1)
    unit_ref: str = Field(alias="UnitRef", min_length=1)
    occupant: str = Field(alias="Occupant", default="")
    start_date: date | None = Field(alias="StartDate")
    end_date: date | None = Field(alias="EndDate")
    annual_rent: Decimal = Field(alias="AnnualRent")
    vacant: Literal["TRUE", "FALSE"] = Field(alias="Vacant")
    period: date = Field(alias="Period")

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _date(cls, v: str) -> date | None:
        return parse_date(v, DATE_FORMAT)

    @field_validator("annual_rent", mode="before")
    @classmethod
    def _amount(cls, v: str) -> Decimal:
        return parse_amount(v)

    @field_validator("vacant", mode="before")
    @classmethod
    def _flag(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("period", mode="before")
    @classmethod
    def _period(cls, v: str) -> date:
        return period_end(v)


class TidewaterLayout(Layout):
    id = "tidewater"
    borrower_id = "tidewater-living"
    borrower_name = "Tidewater Living"
    header = ("PropID", "PropName", "UnitRef", "Occupant", "StartDate", "EndDate", "AnnualRent", "Vacant", "Period")
    row_model = TidewaterRow
    total_unit = "annual rent"

    def split(self, text: str) -> ParsedFile:
        parsed = super().split(text)
        if parsed.data_rows:
            try:
                parsed.as_of_date = period_end(parsed.data_rows[0].values["Period"])
            except ValueError:
                parsed.as_of_date = None
        return parsed

    def is_total(self, row: SourceRow) -> bool:
        return row.values["PropName"].strip().upper() == "TOTALS"

    def read_total(self, row: SourceRow) -> tuple[Decimal | None, int | None]:
        return lenient_amount(row.values["AnnualRent"]), None

    def amount_of(self, row: SourceRow) -> Decimal | None:
        return lenient_amount(row.values["AnnualRent"])

    def map_row(self, typed: BaseModel, parsed: ParsedFile) -> CanonicalRow:
        assert isinstance(typed, TidewaterRow)
        return CanonicalRow(
            borrower_id=self.borrower_id,
            property_code=typed.prop_id,
            property_name=typed.prop_name,
            unit_ref=typed.unit_ref,
            as_of_date=typed.period,
            occupied=typed.vacant == "FALSE",
            monthly_rent=(typed.annual_rent / 12).quantize(CENT, rounding=ROUND_HALF_UP),
            lease_start=typed.start_date,
            lease_end=typed.end_date,
        )
