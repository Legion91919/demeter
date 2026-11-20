from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from demeter.api.app import create_app
from demeter.config import Settings
from demeter.model import Warehouse

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
KEELRIDGE = SAMPLES / "keelridge-estates_2026-10.csv"
MARLOWE = SAMPLES / "marlowe-bay_2026-10.csv"
TIDEWATER_BAD = SAMPLES / "tidewater-living_2026-10_v1-bad-total.csv"
TIDEWATER = SAMPLES / "tidewater-living_2026-10_v2.csv"
VALID = [KEELRIDGE, MARLOWE, TIDEWATER]


class StepClock:
    """Deterministic clock: every call is one second after the last."""

    def __init__(self) -> None:
        self.now = datetime(2026, 11, 2, 6, 0, 0)

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", max_upload_bytes=64 * 1024)


@pytest.fixture
def clock() -> StepClock:
    return StepClock()


@pytest.fixture
def wh(settings: Settings) -> Iterator[Warehouse]:
    store = Warehouse(settings.warehouse_path)
    yield store
    store.close()


@pytest.fixture
def client(settings: Settings, clock: StepClock) -> Iterator[TestClient]:
    with TestClient(create_app(settings, clock)) as c:
        yield c


def upload(client: TestClient, path: Path, layout: str | None = None):
    data = {"layout": layout} if layout else None
    return client.post("/api/loads", files={"file": (path.name, path.read_bytes(), "text/csv")}, data=data)
