from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from rentroll.contracts import Layout, ParsedFile


@dataclass(frozen=True)
class ReconcileResult:
    ok: bool
    reason: str
    computed_total: Decimal | None
    stated_total: Decimal | None
    total_unit: str


def reconcile(parsed: ParsedFile, layout: Layout) -> ReconcileResult:
    """Compare the sum of every data row (valid or not) with the stated total, in the file's own unit.

    This proves we read every row the borrower meant to send. Row-level validity is the clean
    step's job; a row that fails validation still counts here because the borrower counted it.
    """
    unit = parsed.total_unit

    def fail(reason: str, computed: Decimal | None = None) -> ReconcileResult:
        return ReconcileResult(False, reason, computed, parsed.stated_total, unit)

    if not parsed.data_rows:
        return fail("file has no data rows")
    if parsed.total_line_no is None:
        return fail("no total row found; cannot reconcile")
    if parsed.stated_total is None:
        return fail(f"total row (line {parsed.total_line_no}) has no readable amount")
    unreadable = [r.line_no for r in parsed.data_rows if layout.amount_of(r) is None]
    if unreadable:
        lines = ", ".join(str(n) for n in unreadable[:5])
        return fail(f"amount unreadable on line(s) {lines}; cannot reconcile")
    computed = sum((layout.amount_of(r) or Decimal(0) for r in parsed.data_rows), Decimal("0.00"))
    if computed != parsed.stated_total:
        diff = computed - parsed.stated_total
        return fail(
            f"rows sum to {computed:,.2f} {unit} but the total row (line {parsed.total_line_no}) states "
            f"{parsed.stated_total:,.2f} (difference {diff:+,.2f})",
            computed,
        )
    if parsed.stated_units is not None and parsed.stated_units != len(parsed.data_rows):
        return fail(
            f"file has {len(parsed.data_rows)} unit rows but the total row states {parsed.stated_units}", computed
        )
    return ReconcileResult(True, "reconciled", computed, parsed.stated_total, unit)
