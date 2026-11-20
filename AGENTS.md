# AGENTS.md

Rent Roll Pipeline: Borrowers send Harbourline rent rolls in a dozen layouts, so the portfolio view is rebuilt by hand every month and rarely reconciles first time.

## Read first
Everything about this project lives in the hidden `.agentic/` folder.
Start with `.agentic/README.md`; it says which file answers which question.
Load only the files your task needs.

## Hard rules
- Work in thin vertical slices: one ticket from `.agentic/backlog.md` at a time.
- No change without a test that fails first. Run the full test suite before you finish.
- A decision that is hard to reverse gets an ADR in `.agentic/decisions/`.
- Never commit secrets, real client data or personal data. Use `.env.example`.
- Do not grow this file. New knowledge goes in the right `.agentic/` file; history goes in `.agentic/changelog.md`.
- When you learn something that would help on the next project, add it to `.agentic/lessons.md`.
## What is live
- Slice 1 (local): Python 3.12 pipeline in `src/rentroll/` (3 layout contracts, raw landing, reconcile + quarantine, DuckDB model with lineage, FastAPI on :5205, CLI) and the `web/` dashboard (Vite + vanilla TS on :5285).
- Stack differs from the portfolio's .NET default on purpose: see `.agentic/decisions/0002-python-duckdb-stack.md`.
- Checks: `pytest`, `ruff check .`, `cd web && npx vitest run && npm run build`.
