from __future__ import annotations

import ast
from pathlib import Path

from testamur.runtime_inspect import inspect_run
from testamur.runtime_protocol import PROTOCOL_VERSION


class _Client:
    def __init__(self) -> None:
        self.request = None

    def call(self, request):
        self.request = dict(request)
        return {"ok": True, "result": {"run_id": request["run_id"], "state": "finished"}}


def test_inspect_run_preserves_runtime_protocol_shape() -> None:
    client = _Client()
    result = inspect_run(client, "tst:run:abc")
    assert result == {"run_id": "tst:run:abc", "state": "finished"}
    assert client.request["protocol"] == PROTOCOL_VERSION
    assert client.request["operation"] == "get_run"
    assert client.request["run_id"] == "tst:run:abc"
    assert client.request["payload"] == {}


def test_runtime_inspect_has_no_reverse_witness_import() -> None:
    path = Path(__file__).resolve().parents[1] / "testamur" / "runtime_inspect.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert not any(name == "witness" or name.startswith("witness.") for name in imports)
