from __future__ import annotations

import sqlite3
from pathlib import Path

from testamur._work_session_types import UsageState, WorkSessionStatus
from testamur.codex_gateway_hook import CodexGatewayHookBridge, resolve_database_path
from testamur.source_store import TestamurSourceStore


GATEWAY_TOOL = "mcp__testamur_source_gateway__testamur.fetch"


def _start(tmp_path: Path, session_id: str = "thr_secret_host_123") -> dict[str, object]:
    return {
        "session_id": session_id,
        "cwd": str(tmp_path),
        "hook_event_name": "SessionStart",
        "model": "gpt-5.6-codex",
        "permission_mode": "default",
    }


def _tool(tmp_path: Path, *, name: str, use_id: str = "tool_1", tool_input=None, tool_response=None) -> dict[str, object]:
    return {
        "session_id": "thr_secret_host_123",
        "cwd": str(tmp_path),
        "hook_event_name": "PostToolUse",
        "tool_name": name,
        "tool_use_id": use_id,
        "tool_input": {} if tool_input is None else tool_input,
        "tool_response": {} if tool_response is None else tool_response,
    }


def test_session_start_creates_canonical_work_session_without_raw_host_id(tmp_path: Path) -> None:
    db = tmp_path / "evidence.db"
    bridge = CodexGatewayHookBridge(db)
    first = bridge.handle(_start(tmp_path))
    second = bridge.handle(_start(tmp_path))

    assert first["status"] == "session_started"
    assert second["status"] == "session_ready"
    assert first["session_id"] == second["session_id"]
    session = bridge.sessions.get_session(str(first["session_id"]))
    assert session.agent_ref == "codex"
    assert session.host_environment == "codex-hooks"
    assert session.status is WorkSessionStatus.OPEN

    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT host_session_hash,work_session_id FROM testamur_codex_session_bindings"
        ).fetchone()
    assert row is not None
    assert row[0] != "thr_secret_host_123"
    assert row[1] == first["session_id"]
    assert b"thr_secret_host_123" not in db.read_bytes()


def test_structured_gateway_capture_binds_exact_revision_as_fetched(tmp_path: Path) -> None:
    db = tmp_path / "evidence.db"
    bridge = CodexGatewayHookBridge(db)
    started = bridge.handle(_start(tmp_path))

    store = TestamurSourceStore(db)
    locator = "https://example.test/spec?token=secret#frag"
    source = store.get_or_create_source(locator)
    snapshot = store.record_snapshot(
        source["source_id"],
        locator=locator,
        content=b"exact-v1",
        status="captured",
    )
    revision = store.get_revision(snapshot["revision_id"])
    assert revision is not None
    structured = {
        "schema": "testamur.source-gateway.capture.v1",
        "source": source,
        "snapshot": snapshot,
        "revision": revision,
    }

    raw = _tool(
        tmp_path,
        name=GATEWAY_TOOL,
        tool_input={"locator": locator},
        tool_response={"structuredContent": structured, "isError": False},
    )
    result = bridge.handle(raw)
    assert result["status"] == "recorded"
    assert result["usage_state"] == "FETCHED"
    assert result["source_revision_id"] == revision["revision_id"]
    assert result["durable_reliance_implied"] is False

    candidates = bridge.sessions.list_candidates(str(started["session_id"]))
    assert len(candidates) == 1
    assert candidates[0].locator == "https://example.test/spec"
    observations = bridge.sessions.observations(
        str(started["session_id"]), candidate_id=candidates[0].candidate_id
    )
    assert [item.usage_state for item in observations] == [
        UsageState.DISCOVERED,
        UsageState.FETCHED,
    ]

    replay = bridge.handle(raw)
    assert replay["status"] == "idempotent_replay"
    assert len(bridge.sessions.observations(
        str(started["session_id"]), candidate_id=candidates[0].candidate_id
    )) == 2


def test_fabricated_structured_identity_is_not_promoted(tmp_path: Path) -> None:
    bridge = CodexGatewayHookBridge(tmp_path / "evidence.db")
    started = bridge.handle(_start(tmp_path))
    result = bridge.handle(
        _tool(
            tmp_path,
            name=GATEWAY_TOOL,
            tool_input={"locator": "https://example.test/spec?secret=x"},
            tool_response={
                "structuredContent": {
                    "schema": "testamur.source-gateway.capture.v1",
                    "source": {"source_id": "tst:source:fake"},
                    "snapshot": {"snapshot_id": "tst:snapshot:fake"},
                    "revision": {"revision_id": "tst:revision:fake"},
                },
                "isError": False,
            },
        )
    )
    assert result["exact_revision_resolved"] is False
    assert result["source_revision_id"] is None
    candidate = bridge.sessions.list_candidates(str(started["session_id"]))[0]
    observations = bridge.sessions.observations(
        str(started["session_id"]), candidate_id=candidate.candidate_id
    )
    assert [item.usage_state for item in observations] == [UsageState.DISCOVERED]


def test_json_looking_text_is_never_parsed_as_exact_gateway_capture(tmp_path: Path) -> None:
    bridge = CodexGatewayHookBridge(tmp_path / "evidence.db")
    bridge.handle(_start(tmp_path))
    result = bridge.handle(
        _tool(
            tmp_path,
            name=GATEWAY_TOOL,
            tool_input={"url": "https://example.test/a?api_key=secret"},
            tool_response={
                "content": [{"type": "text", "text": '{"schema":"testamur.source-gateway.capture.v1"}'}],
                "isError": False,
            },
        )
    )
    assert result["exact_revision_resolved"] is False
    assert result["locator"] == "https://example.test/a"
    assert "secret" not in result["locator"]


def test_non_source_tool_does_not_create_fake_source_semantics(tmp_path: Path) -> None:
    bridge = CodexGatewayHookBridge(tmp_path / "evidence.db")
    started = bridge.handle(_start(tmp_path))
    result = bridge.handle(
        _tool(
            tmp_path,
            name="apply_patch",
            tool_input={"patch": "sensitive body"},
            tool_response={"ok": True},
        )
    )
    assert result["status"] == "observed_unmapped"
    assert result["semantic_record_created"] is False
    assert bridge.sessions.list_candidates(str(started["session_id"])) == []


def test_session_end_closes_epoch_and_next_start_creates_new_work_session(tmp_path: Path) -> None:
    bridge = CodexGatewayHookBridge(tmp_path / "evidence.db")
    first = bridge.handle(_start(tmp_path))
    ended = bridge.handle({
        "session_id": "thr_secret_host_123",
        "cwd": str(tmp_path),
        "hook_event_name": "SessionEnd",
    })
    assert ended["work_session_status"] == "COMPLETED_UNRECONCILED"
    assert bridge.sessions.get_session(str(first["session_id"])).status is WorkSessionStatus.COMPLETED_UNRECONCILED

    second = bridge.handle(_start(tmp_path))
    assert second["session_id"] != first["session_id"]
    assert bridge.sessions.get_session(str(second["session_id"])).status is WorkSessionStatus.OPEN


def test_late_attach_opens_a_work_session_without_fabricating_prior_history(tmp_path: Path) -> None:
    bridge = CodexGatewayHookBridge(tmp_path / "evidence.db")
    result = bridge.handle(
        _tool(
            tmp_path,
            name="mcp__docs__open_url",
            tool_input={"url": "https://example.test/docs"},
        )
    )
    assert result["late_attach"] is True
    assert result["usage_state"] == "DISCOVERED"
    assert result["source_revision_id"] is None


def test_database_path_defaults_to_workspace_and_supports_override(tmp_path: Path) -> None:
    raw = {"cwd": str(tmp_path)}
    assert resolve_database_path(raw, environ={}) == tmp_path / ".testamur" / "evidence.db"
    assert resolve_database_path(raw, environ={"TESTAMUR_DB": "~/custom.db"}) == Path("~/custom.db").expanduser()
