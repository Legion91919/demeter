from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class LandedFile:
    file_id: str  # sha256 of the bytes; also the stored file name
    original_name: str
    stored_path: Path
    size_bytes: int
    received_at: datetime
    already_landed: bool


def land(raw_dir: Path, content: bytes, original_name: str, received_at: datetime) -> LandedFile:
    """Store the file unchanged. Landing the same bytes again is a no-op (same checksum, same path)."""
    file_id = hashlib.sha256(content).hexdigest()
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{file_id}.csv"
    existed = path.exists()
    if not existed:
        tmp = path.with_suffix(".part")
        tmp.write_bytes(content)
        os.replace(tmp, path)  # atomic: a half-written raw file is never visible
        path.chmod(0o444)  # raw is immutable
    return LandedFile(file_id, Path(original_name).name, path, len(content), received_at, existed)


def read_raw_line(raw_dir: Path, file_id: str, line_no: int) -> str | None:
    """The exact line (1-based) of a landed file, for lineage drill-down."""
    path = raw_dir / f"{file_id}.csv"
    if not path.is_file() or line_no < 1:
        return None
    lines = path.read_bytes().decode("utf-8-sig", errors="replace").splitlines()
    return lines[line_no - 1] if line_no <= len(lines) else None
