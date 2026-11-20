from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import ValidationError

from rentroll.contracts import CanonicalRow, Layout, ParsedFile, SourceRow


@dataclass(frozen=True)
class Reject:
    line_no: int
    reason: str
    raw: str


@dataclass
class CleanResult:
    rows: list[tuple[SourceRow, CanonicalRow]] = field(default_factory=list)
    rejects: list[Reject] = field(default_factory=list)


def _reason(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        parts = []
        for err in exc.errors():
            where = ".".join(str(p) for p in err.get("loc", ()))
            message = str(err.get("msg", "invalid")).removeprefix("Value error, ")
            parts.append(f"{where}: {message}" if where else message)
        return "; ".join(parts)
    return str(exc)


def clean(parsed: ParsedFile, layout: Layout) -> CleanResult:
    """Validate every data row against the layout contract and the shared rules."""
    result = CleanResult()
    seen: dict[tuple, int] = {}
    for source in parsed.data_rows:
        try:
            row = layout.to_canonical(source, parsed)
        except ValueError as exc:  # pydantic ValidationError is a ValueError
            result.rejects.append(Reject(source.line_no, _reason(exc), source.raw))
            continue
        if parsed.as_of_date and row.as_of_date != parsed.as_of_date:
            result.rejects.append(
                Reject(
                    source.line_no,
                    f"as-of date {row.as_of_date} differs from the file's {parsed.as_of_date}",
                    source.raw,
                )
            )
            continue
        if row.natural_key in seen:
            result.rejects.append(
                Reject(
                    source.line_no, f"duplicate unit {row.unit_ref} (first on line {seen[row.natural_key]})", source.raw
                )
            )
            continue
        seen[row.natural_key] = source.line_no
        result.rows.append((source, row))
    return result
