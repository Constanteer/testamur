from __future__ import annotations

import ast
from pathlib import Path

from testamur.agent_wrapper import (
    AGENT_WRAPPER_VERSION,
    _looks_like_recursive_testamur_run,
    _predicted_run_id,
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def test_canonical_agent_wrapper_has_no_retired_runtime_imports() -> None:
    root = Path(__file__).resolve().parents[1]
    imports = _imports(root / "testamur" / "agent_wrapper.py")
    assert not any(
        name in {"witness", "witness_service"}
        or name.startswith(("witness.", "witness_service."))
        for name in imports
    )


def test_agent_wrapper_new_write_identity_is_testamur_owned() -> None:
    assert AGENT_WRAPPER_VERSION == "testamur-agent-wrapper-v0.4"
    run_id = _predicted_run_id(
        {
            "client_id": "testamur-agent-wrapper",
            "request_id": "req-test",
            "idempotency_key": "stable-key",
            "argv": ["echo", "ok"],
            "cwd": ".",
            "timeout_seconds": 30,
        }
    )
    assert run_id.startswith("tst:run:")


def test_recursive_testamur_run_is_rejected_before_execution() -> None:
    assert _looks_like_recursive_testamur_run(["testamur", "run", "--", "echo", "ok"])
    assert _looks_like_recursive_testamur_run(["testamur", "--", "echo", "ok"])
    assert _looks_like_recursive_testamur_run(["python3", "-m", "testamur", "run", "--", "echo", "ok"])
    assert _looks_like_recursive_testamur_run(["python3", "-m", "testamur", "--", "echo", "ok"])
    assert _looks_like_recursive_testamur_run(
        ["python3", "-m", "testamur.front_router", "run", "--", "echo", "ok"]
    )


def test_historical_witness_run_shape_remains_conservatively_recursive() -> None:
    assert _looks_like_recursive_testamur_run(["witness", "run", "--", "echo", "ok"])
    assert _looks_like_recursive_testamur_run(
        ["python3", "-m", "witness.runtime_cli", "run", "--", "echo", "ok"]
    )


def test_witness_runtime_package_is_retired() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "witness").exists()
    assert not (root / "witness_service").exists()
