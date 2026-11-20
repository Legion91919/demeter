"""API tests with FastAPI's TestClient: the slice-1 journey over HTTP."""

from __future__ import annotations

from conftest import KEELRIDGE, MARLOWE, TIDEWATER, TIDEWATER_BAD, VALID, upload


def test_health(client):
    assert client.get("/health/live").json() == {"status": "live"}
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_layouts_lists_the_three_contracts(client):
    assert {x["layout_id"] for x in client.get("/api/layouts").json()} == {"keelridge", "marlowe", "tidewater"}


def test_ac1_upload_twice_over_http_keeps_portfolio_unchanged(client):
    assert upload(client, KEELRIDGE).status_code == 201
    before = client.get("/api/portfolio").json()["properties"]
    again = upload(client, KEELRIDGE)
    assert again.status_code == 201
    after = client.get("/api/portfolio").json()["properties"]
    strip = [{k: v for k, v in p.items() if k not in {"loaded_at", "job_run_id"}} for p in before]
    assert strip == [{k: v for k, v in p.items() if k not in {"loaded_at", "job_run_id"}} for p in after]
    assert len(client.get("/api/job-runs").json()) == 2


def test_ac2_mismatched_total_returns_422_problem_with_reason_and_job_run(client):
    response = upload(client, TIDEWATER_BAD)
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["title"] == "File quarantined" and "difference +4,000.00" in body["detail"]
    assert body["job_run"]["status"] == "quarantined"
    assert client.get("/api/portfolio").json()["properties"] == []
    assert client.get("/api/quarantine").json()["files"][0]["original_name"] == TIDEWATER_BAD.name
    assert client.get("/api/portfolio").json()["freshness"]["files_in_quarantine"] == 1


def test_ac3_lineage_endpoint_returns_source_file_row_and_raw_line(client):
    run = upload(client, TIDEWATER).json()
    body = client.get("/api/properties/tidewater-living/TW9/lineage").json()
    assert body["property_name"] == "Breakwater House"
    first = body["rows"][0]
    assert first["source_file_name"] == TIDEWATER.name
    assert first["source_row"] == 6 and first["job_run_id"] == run["job_run_id"]
    assert first["raw_line"].startswith("TW9,Breakwater House,1,")
    assert first["monthly_rent"] == "40500.00"


def test_lineage_for_unknown_property_is_404(client):
    response = client.get("/api/properties/nobody/x/lineage")
    assert response.status_code == 404 and response.json()["status"] == 404


def test_portfolio_totals_freshness_and_money_as_strings(client):
    for path in VALID:
        assert upload(client, path).status_code == 201
    body = client.get("/api/portfolio").json()
    assert body["totals"]["properties"] == 6
    assert body["totals"]["units"] == 22 and body["totals"]["occupied_units"] == 16
    assert body["totals"]["monthly_rent"] == "384282.42"  # 164515.75 + 102075.00 + 117691.67
    assert body["freshness"]["latest_as_of_date"] == "2026-10-31"
    assert body["freshness"]["last_successful_load_at"].endswith("Z")
    assert all(isinstance(p["monthly_rent"], str) for p in body["properties"])


def test_job_run_detail_and_404(client):
    run = upload(client, MARLOWE).json()
    detail = client.get(f"/api/job-runs/{run['job_run_id']}").json()
    assert detail["rows_rejected"] == 1 and detail["message"].endswith("1 row(s) quarantined")
    assert client.get("/api/job-runs/missing").status_code == 404


def test_explicit_layout_and_upload_limits(client):
    assert upload(client, KEELRIDGE, layout="keelridge").status_code == 201
    empty = client.post("/api/loads", files={"file": ("e.csv", b"", "text/csv")})
    assert empty.status_code == 400
    big = client.post("/api/loads", files={"file": ("b.csv", b"x" * (64 * 1024 + 1), "text/csv")})
    assert big.status_code == 413
