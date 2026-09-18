from __future__ import annotations

import ast
from pathlib import Path


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def test_canonical_graph_query_modules_have_no_witness_imports() -> None:
    root = Path(__file__).resolve().parents[1]
    for relative in (
        "testamur/query.py",
        "testamur/inspector.py",
        "testamur/runtime_graph_query.py",
    ):
        imports = _imports(root / relative)
        assert not any(name == "witness" or name.startswith("witness.") for name in imports), relative


def test_graph_query_reexports_canonical_testamur_query() -> None:
    from testamur.graph_query import TestamurQuery as exported
    from testamur.query import TestamurQuery as canonical

    assert exported is canonical
