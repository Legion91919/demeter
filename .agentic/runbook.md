# Runbook

## Prerequisites
Python 3.12, Node 22. Install pinned dependencies:
```bash
pip install -r requirements.lock          # add --break-system-packages on a system Python
cd web && npm ci && cd ..
```

## Run locally
```bash
PYTHONPATH=src uvicorn demeter.api.app:app --port 5205     # API on http://localhost:5205 (docs at /docs)
cd web && npm run dev                                        # dashboard on http://localhost:5285, proxies /api to :5205
```
Data lives in `data/` (git-ignored): `data/warehouse.duckdb` and `data/raw/<sha256>.csv`. Override with `RENTROLL_DATA_DIR`.

Load files without the web:
```bash
PYTHONPATH=src python -m demeter.cli load samples/*.csv     # exit 1 if any file was quarantined (the broken sample is)
```
Rebuild the invented samples: `python3 tools/make_samples.py`.

## Tests
```bash
pytest --cov --cov-fail-under=80        # contracts, rules, pipeline, API, boundaries
ruff check . && ruff format --check .
cd web && npx vitest run && npm run build
```

## Smoke test
```bash
PYTHONPATH=src uvicorn demeter.api.app:app --port 5205 &
for f in samples/*.csv; do curl -s -o /dev/null -w "$f %{http_code}\n" -F "file=@$f" http://localhost:5205/api/loads; done
curl -s http://localhost:5205/api/portfolio
curl -s http://localhost:5205/api/properties/keelridge-estates/KR-01/lineage
kill %1
```
Expected: three `201`, one `422` (`tidewater-living_2026-10_v1-bad-total.csv`), 6 properties, 72.7% occupied, R 384,282.42 a month.

## Deploy
Not deployed yet (slice 1 is local with invented data). Target: one container (uvicorn, single worker) with a persistent volume for `data/`, behind SSO; the dashboard as static files from `web/dist`. Back up `data/` nightly; raw files are the replay source.

## Monitor and alerts
- `GET /health/live` (process up), `GET /health/ready` (warehouse reachable, 503 otherwise).
- `GET /api/job-runs`: status, rows read/written/rejected and duration per run. Alert on any `failed` run; chase any `quarantined` file at month-end.

## Common incidents
| Symptom | Cause | Fix |
|---|---|---|
| Upload returns 422 "rows sum to ... but the total row states ..." | borrower's total is wrong or rows are missing | send the reason to the borrower; load the corrected file (it replaces the month) |
| 422 "no single known layout matches" | new borrower or changed layout | add/version a contract in `src/demeter/contracts/` with a sample and contract test, then re-load the raw file from `data/raw/` |
| Job run `failed` | bug or disk problem; nothing was written (transaction rolled back) | read the log line for the job run id, fix, re-load the same file |
| `/health/ready` 503 / "database is locked" | a second process opened the DuckDB file | run one API process; stop the other (DuckDB allows one writer process) |
