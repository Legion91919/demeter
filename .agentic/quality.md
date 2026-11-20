# Quality

## Definition of done
- Acceptance criteria met and demonstrated, each with at least one test (`docs/DESIGN.md` section 13 maps them).
- Contract test per borrower layout on its sample file; rules unit-tested; pipeline tested against a real DuckDB file; API tested with TestClient; boundary test green.
- CI green: ruff, pytest with coverage >= 80% (ratchet up only), samples reproducible, pip-audit, web vitest + build, gitleaks, privacy guard.
- Docs in `.agentic/` updated in the same change.

## Service levels
| SLI | SLO |
|---|---|
| Freshness: file received -> portfolio updated | < 1 h for 99% of files (today < 1 s) |
| Reconciliation: loaded files whose rows equal their stated total | 100% (mismatches are quarantined, never loaded) |
| Lineage coverage: fact rows with source file, row and job run id | 100% (NOT NULL columns) |
| Job runs closed (not left `running`) | 100% |
| API success rate (non-4xx) | 99.9% over 30 days |
| p95 API latency (portfolio, lineage) | < 300 ms |

## Current numbers (2026-11-20)
- pytest: 42 passed, coverage 93% (cli.py untested directly; covered by the smoke run).
- vitest: 11 passed. `npm run build` passes.
- Smoke: 4 sample files -> 3 loaded, 1 quarantined; load ~25 ms per file.
