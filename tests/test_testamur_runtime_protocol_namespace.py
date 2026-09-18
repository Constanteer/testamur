from __future__ import annotations

from testamur import runtime_protocol
from testamur.command_execution import COMMAND_EXECUTION_VERSION


def _begin_request() -> dict[str, object]:
    return {
        "protocol": runtime_protocol.PROTOCOL_VERSION,
        "client_id": "namespace-migration-test",
        "request_id": "req-1",
        "idempotency_key": "begin-1",
        "operation": "begin_run",
        "payload": {"cwd": "/tmp/example", "argv": ["echo", "ok"]},
    }


def test_testamur_runtime_protocol_is_canonical_python_surface() -> None:
    assert runtime_protocol.RuntimeProtocol.__module__ == "testamur.runtime_protocol"
    assert runtime_protocol.MemoryProtocolLedger.__module__ == "testamur.runtime_protocol"


def test_new_wire_identity_is_testamur_owned_and_legacy_token_is_explicit() -> None:
    assert runtime_protocol.PROTOCOL_VERSION == "testamur-runtime-v0.1"
    assert COMMAND_EXECUTION_VERSION == "testamur-command-v0.1"
    assert runtime_protocol.LEGACY_PROTOCOL_VERSION == "witness-runtime-v0.1"


def test_testamur_runtime_begin_run_and_error_semantics() -> None:
    runtime = runtime_protocol.RuntimeProtocol()
    current = runtime.call(_begin_request())
    assert current["ok"] is True
    assert current["protocol"] == runtime_protocol.PROTOCOL_VERSION
    assert current["result"]["run_id"].startswith("tst:run:")

    request = _begin_request()
    request["request_id"] = "req-invalid"
    request["idempotency_key"] = "invalid-protocol"
    request["protocol"] = runtime_protocol.LEGACY_PROTOCOL_VERSION
    error = runtime.safe_call(request)
    assert error["ok"] is False
    assert error["protocol"] == runtime_protocol.PROTOCOL_VERSION
    assert error["error"]["code"] == "invalid_request"


def test_testamur_runtime_event_identity_is_testamur_owned() -> None:
    runtime = runtime_protocol.RuntimeProtocol()
    begin = runtime.call(_begin_request())
    run_id = begin["result"]["run_id"]
    event = {
        "protocol": runtime_protocol.PROTOCOL_VERSION,
        "client_id": "namespace-migration-test",
        "request_id": "req-2",
        "idempotency_key": "event-1",
        "operation": "observe_artifact",
        "run_id": run_id,
        "sequence": 1,
        "payload": {"path": "result.txt", "content_hash": "sha256:abc"},
    }
    response = runtime.call(event)
    assert response["ok"] is True
    assert response["protocol"] == runtime_protocol.PROTOCOL_VERSION
    assert response["result"]["run_id"] == run_id
    assert response["result"]["event_id"].startswith("tst:event:")
