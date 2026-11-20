from __future__ import annotations

from pathlib import Path
from typing import Any

from demeter.ingest import read_raw_line
from demeter.model import Warehouse


def property_lineage(wh: Warehouse, raw_dir: Path, borrower_id: str, property_code: str) -> dict[str, Any] | None:
    """The rows behind one dashboard figure, each with the exact line from the unchanged source file."""
    prop = wh.property(borrower_id, property_code)
    if prop is None:
        return None
    rows = wh.property_lineage(borrower_id, property_code)
    for row in rows:
        row["raw_line"] = read_raw_line(raw_dir, row["source_file_id"], row["source_row"])
    return {**prop, "rows": rows}
