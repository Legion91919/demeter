# 0002. Python, FastAPI and DuckDB for this product

- Status: Accepted
- Date: 2026-11-20

## Context

ADR-0001 chose one re-runnable import job per layout into a single warehouse, with a read-only dashboard. The rest of the portfolio is .NET. This product is a batch data pipeline: CSV parsing, per-layout contracts, set-based reconciliation and a few read endpoints. The team is one engineer plus an analyst, and the analyst already works in Python notebooks.

## Decision

- Python 3.12, pydantic models as the per-layout data contracts, FastAPI + uvicorn for the API, pytest for tests.
- DuckDB as the warehouse: one file under `data/` (git-ignored), opened in-process. Facts are upserted with `INSERT ... ON CONFLICT DO UPDATE` on the natural key.
- Raw files are stored unchanged under `data/raw/<sha256>.csv`.
- Web: Vite + vanilla TypeScript (no framework): one screen, a few tables.

## Alternatives considered

- .NET 8 + SQL Server/Postgres (the portfolio default): strong, but more ceremony for a CSV-shaped problem, and the analyst could not read or extend the contracts.
- Postgres as the warehouse now: the right next step for concurrent writers and hosted backups; today it adds a server to run for ~20k rows a month.
- Spark/Databricks: one machine handles this volume ~1000x over.
- Serverless functions per file: fits bursty imports, but split the job across cold-started functions and make the end-to-end test and lineage harder for a one-engineer team.
- Streaming (Kafka etc.): rent rolls arrive monthly as files; there is no stream.

## Consequences

- One process, one file: trivial to run and back up, impossible to share between several writer processes. Loads are serialised by an in-process lock.
- Evolve when: a second writer process, hosted multi-user access or > ~50 GB of data appears. Then move the warehouse to Postgres (the SQL is plain and portable) and keep the contracts and jobs unchanged.
