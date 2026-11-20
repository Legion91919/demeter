"""Layout A: Keelridge Estates (invented borrower).

property_code,property_name,unit_no,tenant,lease_start,lease_end,monthly_rent,status,roll_date
- ISO dates (yyyy-mm-dd), plain monthly amounts, status OCCUPIED / VACANT
- roll date repeated on every row
- last row: property_code = TOTAL, monthly_rent = stated monthly total (no unit count)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import CanonicalRow, Layout, ParsedFile, SourceRow, lenient_amount, parse_amount, parse_date

DATE_FORMAT = "%Y-%m-%d"


class KeelridgeRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    property_code: str = Field(min_length=1)
    property_name: str = Field(min_length=1)
    unit_no: str = Field(min_length=1)
    tenant: str = ""
    lease_start: date | None
    lease_end: date | None
    monthly_rent: Decimal
    status: Literal["OCCUPIED", "VACANT"]
    roll_date: date

    @field_validator("lease_start", "lease_end", "roll_date", mode="before")
    @classmethod
    def _date(cls, v: str) -> date | None:
        return parse_date(v, DATE_FORMAT)

    @field_validator("monthly_rent", mode="before")
    @classmethod
    def _amount(cls, v: str) -> Decimal:
        return parse_amount(v)

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, v: str) -> str:
        return v.strip().upper()


class KeelridgeLayout(Layout):
    id = "keelridge"
    borrower_id = "keelridge-estates"
    borrower_name = "Keelridge Estates"
    header = (
        "property_code",
        "property_name",
        "unit_no",
        "tenant",
        "lease_start",
        "lease_end",
        "monthly_rent",
        "status",
        "roll_date",
    )
    row_model = KeelridgeRow

    def split(self, text: str) -> ParsedFile:
        parsed = super().split(text)
        if parsed.data_rows:
            try:
                parsed.as_of_date = parse_date(parsed.data_rows[0].values["roll_date"], DATE_FORMAT)
            except ValueError:
                parsed.as_of_date = None
        return parsed

    def is_total(self, row: SourceRow) -> bool:
        return row.values["property_code"].strip().upper() == "TOTAL"

    def read_total(self, row: SourceRow) -> tuple[Decimal | None, int | None]:
        return lenient_amount(row.values["monthly_rent"]), None

    def amount_of(self, row: SourceRow) -> Decimal | None:
        return lenient_amount(row.values["monthly_rent"])

    def map_row(self, typed: BaseModel, parsed: ParsedFile) -> CanonicalRow:
        assert isinstance(typed, KeelridgeRow)
        return CanonicalRow(
            borrower_id=self.borrower_id,
            property_code=typed.property_code,
            property_name=typed.property_name,
            unit_ref=typed.unit_no,
            as_of_date=typed.roll_date,
            occupied=typed.status == "OCCUPIED",
            monthly_rent=typed.monthly_rent,
            lease_start=typed.lease_start,
            lease_end=typed.lease_end,
        )
