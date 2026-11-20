"""FastAPI composition root: load endpoint, job runs, portfolio, lineage, quarantine and health."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from demeter import contracts
from demeter.config import Clock, Settings, utc_now
from demeter.jobs import run_load
from demeter.lineage import property_lineage
from demeter.model import Warehouse

PROBLEM = "application/problem+json"


def jsonable(value: Any) -> Any:
    """Money stays exact: Decimals go out as strings; timestamps as UTC ISO-8601."""
    if isinstance(value, Decimal):
        return f"{value:.2f}" if value.as_tuple().exponent == -2 else str(value)
    if isinstance(value, datetime):
        return value.isoformat() + "Z"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    return value


def ok(body: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(jsonable(body), status_code=status)


def problem(status: int, title: str, detail: str, **extra: Any) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail, **jsonable(extra)}
    return JSONResponse(body, status_code=status, media_type=PROBLEM)


def create_app(settings: Settings | None = None, clock: Clock = utc_now) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.wh = Warehouse(settings.warehouse_path)
        try:
            yield
        finally:
            app.state.wh.close()

    app = FastAPI(title="Harbourline rent-roll pipeline", version="0.1.0", lifespan=lifespan)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    def wh(request: Request) -> Warehouse:
        return request.app.state.wh

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def ready(request: Request) -> JSONResponse:
        try:
            wh(request).ping()
        except Exception as exc:  # noqa: BLE001 - readiness reports any dependency failure
            return problem(503, "Not ready", f"warehouse unavailable: {exc}")
        return ok({"status": "ready"})

    @app.get("/api/layouts")
    def layouts() -> list[dict[str, Any]]:
        return [
            {
                "layout_id": layout.id,
                "borrower_id": layout.borrower_id,
                "borrower_name": layout.borrower_name,
                "header": list(layout.header),
                "total_unit": layout.total_unit,
            }
            for layout in contracts.LAYOUTS.values()
        ]

    @app.post("/api/loads")
    async def load(request: Request, file: UploadFile = File(...), layout: str | None = Form(None)) -> JSONResponse:
        content = await file.read(settings.max_upload_bytes + 1)
        if len(content) > settings.max_upload_bytes:
            return problem(413, "File too large", f"rent rolls are limited to {settings.max_upload_bytes} bytes")
        if not content:
            return problem(400, "Empty file", "the uploaded file has no content")
        run = run_load(wh(request), settings, content, file.filename or "upload.csv", layout or None, clock)
        if run["status"] == "succeeded":
            return ok(run, 201)
        if run["status"] == "quarantined":
            return problem(422, "File quarantined", run["message"], job_run=run)
        return problem(500, "Load failed", run["message"], job_run=run)

    @app.get("/api/job-runs")
    def job_runs(request: Request, limit: int = 50) -> JSONResponse:
        return ok(wh(request).job_runs(max(1, min(limit, 500))))

    @app.get("/api/job-runs/{job_run_id}")
    def job_run(request: Request, job_run_id: str) -> JSONResponse:
        run = wh(request).job_run(job_run_id)
        return ok(run) if run else problem(404, "Not found", f"no job run {job_run_id}")

    @app.get("/api/portfolio")
    def portfolio(request: Request) -> JSONResponse:
        store = wh(request)
        properties = store.portfolio()
        units = sum(p["units"] for p in properties)
        occupied = sum(p["occupied_units"] for p in properties)
        totals = {
            "properties": len(properties),
            "units": units,
            "occupied_units": occupied,
            "occupancy_pct": (Decimal(100) * occupied / units).quantize(Decimal("0.1")) if units else None,
            "monthly_rent": sum((p["monthly_rent"] for p in properties), Decimal("0.00")),
        }
        return ok({"freshness": store.freshness(), "totals": totals, "properties": properties})

    @app.get("/api/properties/{borrower_id}/{property_code}/lineage")
    def lineage(request: Request, borrower_id: str, property_code: str) -> JSONResponse:
        found = property_lineage(wh(request), settings.raw_dir, borrower_id, property_code)
        if found is None:
            return problem(404, "Not found", f"no property {borrower_id}/{property_code}")
        return ok(found)

    @app.get("/api/quarantine")
    def quarantine(request: Request) -> JSONResponse:
        return ok(wh(request).quarantine())

    return app


app = create_app()
