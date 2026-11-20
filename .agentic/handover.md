# Handover

What the client needs to own this without us.

- [ ] Source, infrastructure-as-code and pipelines in the client's own accounts
- [ ] Every secret rotated and owned by the client
- [ ] Architecture and decisions explained (`architecture.md`, `decisions/`)
- [ ] Runbook rehearsed by a client engineer
- [ ] Known issues and next steps listed below
- [ ] AI agent setup documented so their team can keep using it

## Known issues
- No authentication yet; local use with invented data only.
- DuckDB allows one writer process: run a single uvicorn worker until the Postgres move (ADR-0002).
- Row-wise upserts: fine to ~50k rows per file; switch to set-based staging beyond that.
- CSV fields with embedded line breaks are not supported (each physical line is one row, which keeps line-number lineage exact).

## Recommended next steps
- Get CI green on GitHub, then slices 2 and 3 from `backlog.md`.
- Add SSO before loading any real borrower file.