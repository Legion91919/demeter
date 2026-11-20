#!/usr/bin/env bash
# Runs every test suite in this repo, the same way CI does.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "==> ruff check ."
ruff check .
echo "==> ruff format --check ."
ruff format --check .
echo "==> pytest --cov --cov-fail-under=80"
pytest --cov --cov-fail-under=80
echo "==> (cd web && npx vitest run && npm run build)"
(cd web && npx vitest run && npm run build)
echo 'All tests passed.'
