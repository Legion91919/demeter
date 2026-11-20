"""One data contract per borrower layout, plus the registry that picks one for a file."""

from __future__ import annotations

from .base import CanonicalRow, Layout, LayoutError, ParsedFile, SourceRow
from .keelridge import KeelridgeLayout
from .marlowe import MarloweLayout
from .tidewater import TidewaterLayout

LAYOUTS: dict[str, Layout] = {layout.id: layout for layout in (KeelridgeLayout(), MarloweLayout(), TidewaterLayout())}


def resolve(text: str, layout_id: str | None = None) -> Layout | None:
    """The named layout, or the single layout whose header signature matches the file."""
    if layout_id:
        return LAYOUTS.get(layout_id)
    matches = [layout for layout in LAYOUTS.values() if layout.detects(text)]
    return matches[0] if len(matches) == 1 else None


__all__ = ["LAYOUTS", "CanonicalRow", "Layout", "LayoutError", "ParsedFile", "SourceRow", "resolve"]
