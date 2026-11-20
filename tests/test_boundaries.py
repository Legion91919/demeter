"""Boundary tests: the inner layers never import the outer ones (reflection over imports)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "rentroll"

# module -> packages it must never import
FORBIDDEN = {
    "contracts": {"duckdb", "fastapi", "rentroll.model", "rentroll.api", "rentroll.jobs", "rentroll.ingest"},
    "reconcile": {"duckdb", "fastapi", "rentroll.model", "rentroll.api", "rentroll.jobs"},
    "clean": {"duckdb", "fastapi", "rentroll.model", "rentroll.api", "rentroll.jobs"},
    "ingest": {"duckdb", "fastapi", "rentroll.model", "rentroll.api"},
    "model": {"fastapi", "rentroll.api", "rentroll.jobs"},
    "lineage": {"fastapi", "rentroll.api", "rentroll.jobs"},
}


def imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


@pytest.mark.parametrize("module", sorted(FORBIDDEN))
def test_module_does_not_reach_outwards(module):
    for path in (SRC / module).glob("*.py"):
        for name in imports(path):
            hit = [f for f in FORBIDDEN[module] if name == f or name.startswith(f + ".")]
            assert not hit, f"{path.name} imports {name}"
