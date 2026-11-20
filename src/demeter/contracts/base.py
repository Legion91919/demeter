"""The shared data contract every borrower layout maps onto, and the base class for layouts.

A layout contract knows three things about one borrower's file:
1. how to recognise it (header signature),
2. how to split it into data rows and the borrower's stated total row,
3. how to turn one data row into a `CanonicalRow` (typed, validated) via its own pydantic row model.
"""

from __future__ import annotations

import csv
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

CENT = Decimal("0.01")


class CanonicalRow(BaseModel):
    """One unit on one borrower's rent roll at one as-of date. The clean-layer contract."""

    model_config = ConfigDict(frozen=True)

    borrower_id: str = Field(min_length=1)
    property_code: str = Field(min_length=1)
    property_name: str = Field(min_length=1)
    unit_ref: str = Field(min_length=1)
    as_of_date: date
    occupied: bool
    monthly_rent: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    lease_start: date | None = None
    lease_end: date | None = None

    @model_validator(mode="after")
    def _rules(self) -> CanonicalRow:
        if self.lease_start and self.lease_end and self.lease_end < self.lease_start:
            raise ValueError("lease ends before it starts")
        if self.occupied and self.monthly_rent == 0:
            raise ValueError("occupied unit has no rent")
        if not self.occupied and self.monthly_rent != 0:
            raise ValueError("vacant unit has rent")
        return self

    @property
    def natural_key(self) -> tuple[str, str, str, date]:
        return (self.borrower_id, self.property_code, self.unit_ref, self.as_of_date)


@dataclass(frozen=True)
class SourceRow:
    """One physical line of the file (1-based line number) and its cells keyed by header."""

    line_no: int
    values: dict[str, str]
    raw: str


@dataclass
class ParsedFile:
    layout_id: str
    borrower_id: str
    as_of_date: date | None
    data_rows: list[SourceRow] = field(default_factory=list)
    stated_total: Decimal | None = None
    stated_units: int | None = None
    total_line_no: int | None = None
    total_unit: str = "monthly rent"


class LayoutError(ValueError):
    """The file does not have the shape this layout promises (missing header, bad preamble)."""


def parse_amount(text: str) -> Decimal:
    """'12,800.00' -> Decimal('12800.00'). Raises ValueError on anything that isn't money."""
    cleaned = text.strip().replace(",", "").replace(" ", "")
    if not cleaned:
        raise ValueError("amount is blank")
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"amount '{text}' is not a number") from exc
    if not value.is_finite():
        raise ValueError(f"amount '{text}' is not a number")
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def parse_date(text: str, fmt: str) -> date | None:
    text = text.strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, fmt).date()
    except ValueError as exc:
        raise ValueError(f"date '{text}' is not in the form {fmt}") from exc


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")


class Layout(ABC):
    """Base class for one borrower layout. Subclasses set the class vars and three hooks."""

    id: ClassVar[str]
    borrower_id: ClassVar[str]
    borrower_name: ClassVar[str]
    header: ClassVar[tuple[str, ...]]
    row_model: ClassVar[type[BaseModel]]
    total_unit: ClassVar[str] = "monthly rent"
    delimiter: ClassVar[str] = ","

    # ---- recognise -------------------------------------------------------------------
    def find_header(self, lines: list[str]) -> int | None:
        for index, line in enumerate(lines[:10]):
            if tuple(c.strip() for c in self._cells(line)) == self.header:
                return index
        return None

    def detects(self, text: str) -> bool:
        return self.find_header(text.splitlines()) is not None

    # ---- split -----------------------------------------------------------------------
    def split(self, text: str) -> ParsedFile:
        lines = text.splitlines()
        header_index = self.find_header(lines)
        if header_index is None:
            raise LayoutError(f"header row for layout '{self.id}' not found")
        parsed = ParsedFile(
            layout_id=self.id,
            borrower_id=self.borrower_id,
            as_of_date=self.preamble_as_of(lines[:header_index]),
            total_unit=self.total_unit,
        )
        for index in range(header_index + 1, len(lines)):
            line = lines[index]
            if not line.strip():
                continue
            cells = self._cells(line)
            cells += [""] * (len(self.header) - len(cells))
            row = SourceRow(line_no=index + 1, values=dict(zip(self.header, cells, strict=False)), raw=line)
            if self.is_total(row):
                parsed.total_line_no = row.line_no
                parsed.stated_total, parsed.stated_units = self.read_total(row)
                break
            parsed.data_rows.append(row)
        return parsed

    def _cells(self, line: str) -> list[str]:
        return next(csv.reader([line], delimiter=self.delimiter), [])

    def preamble_as_of(self, preamble: list[str]) -> date | None:
        return None

    @abstractmethod
    def is_total(self, row: SourceRow) -> bool: ...

    @abstractmethod
    def read_total(self, row: SourceRow) -> tuple[Decimal | None, int | None]: ...

    @abstractmethod
    def amount_of(self, row: SourceRow) -> Decimal | None:
        """The row's amount in the same unit as the stated total, for reconciliation."""

    # ---- map -------------------------------------------------------------------------
    def to_canonical(self, row: SourceRow, parsed: ParsedFile) -> CanonicalRow:
        """Validate the row against this layout's row model, then map it. Raises ValueError."""
        typed = self.row_model.model_validate(row.values)
        return self.map_row(typed, parsed)

    @abstractmethod
    def map_row(self, typed: BaseModel, parsed: ParsedFile) -> CanonicalRow: ...


def lenient_amount(text: str) -> Decimal | None:
    try:
        return parse_amount(text)
    except ValueError:
        return None
