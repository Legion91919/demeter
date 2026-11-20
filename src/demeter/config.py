"""Settings from the environment, with safe local defaults. No secrets are needed in slice 1."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """UTC wall-clock time without tzinfo (DuckDB TIMESTAMP columns hold UTC)."""
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    max_upload_bytes: int = 5 * 1024 * 1024

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def warehouse_path(self) -> Path:
        return self.data_dir / "warehouse.duckdb"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=Path(os.environ.get("RENTROLL_DATA_DIR", "data")),
            max_upload_bytes=int(os.environ.get("RENTROLL_MAX_UPLOAD_BYTES", str(5 * 1024 * 1024))),
        )
