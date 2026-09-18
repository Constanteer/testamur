from __future__ import annotations

import json

import pytest

from testamur._work_session_types import UsageState
from testamur.source_fetch import SourceFetchResult
from testamur.source_gateway import TestamurSourceGateway
from testamur.source_gateway_cli import main as gateway_main


def _start(gateway: TestamurSourceGateway, session_id: str) -> None:
    gateway.sessions.start_session(
        initiating_actor_ref="test:actor",
        host_environment="pytest",
        project_ref="tst:project:test",
        agent_ref="codex",
        agent_version="test",
        session_id=session_id,
    )


def test_gateway_exact_capture_retains_bytes_and_reuses_revision(monkeypatch, tmp_path):
    body = b"exact revision bytes\n"

    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(
            requested_locator=locator,
            final_locator=locator,
            status="captured",
            content=body,
            metadata={"status_code": 200, "content_type": "text/plain"},
        )

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    gateway = TestamurSourceGateway(tmp_path / "evidence.db")

    first = gateway.fetch("https://example.test/spec")
    second = gateway.fetch("https://example.test/spec")

    assert first.revision is not None
    assert second.revision is not None
    assert first.revision["revision_id"] == second.revision["revision_id"]
    assert first.snapshot["snapshot_id"] != second.snapshot["snapshot_id"]
    assert first.blob is not None
    assert first.snapshot["content_hash"] == first.blob["content_hash"]
    assert gateway.open_revision(first.revision["revision_id"]) == body
    assert gateway.sources.stats()["sources"] == 1
    assert gateway.sources.stats()["revisions"] == 1
    assert gateway.sources.stats()["snapshots"] == 2
    assert first.metadata()["semantics"]["durable_reliance_implied"] is False


def test_gateway_unavailable_capture_does_not_fabricate_revision(monkeypatch, tmp_path):
    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(
            requested_locator=locator,
            final_locator=locator,
            status="unavailable",
            content=None,
            metadata={"error": {"kind": "transport_error", "message": "offline"}},
        )

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    gateway = TestamurSourceGateway(tmp_path / "evidence.db")
    result = gateway.fetch("https://example.test/offline")

    assert result.revision is None
    assert result.blob is None
    assert result.snapshot["revision_id"] is None
    assert result.snapshot["status"] == "unavailable"
    assert result.metadata()["semantics"]["exact_revision_captured"] is False


def test_invalid_session_binding_fails_before_network_or_source_side_effect(monkeypatch, tmp_path):
    calls = []

    def fake_fetch(locator, *, policy=None):
        calls.append(locator)
        return SourceFetchResult(locator, locator, "captured", b"should-not-run", {})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    gateway = TestamurSourceGateway(tmp_path / "evidence.db")

    with pytest.raises(KeyError):
        gateway.fetch(
            "https://example.test/spec",
            session_id="tst:work-session:missing",
        )

    assert calls == []
    assert gateway.sources.stats() == {
        "sources": 0,
        "revisions": 0,
        "snapshots": 0,
        "snapshots_without_revision": 0,
    }


def test_closed_session_binding_fails_before_network(monkeypatch, tmp_path):
    calls = []

    def fake_fetch(locator, *, policy=None):
        calls.append(locator)
        return SourceFetchResult(locator, locator, "captured", b"should-not-run", {})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    gateway = TestamurSourceGateway(tmp_path / "evidence.db")
    session = "tst:work-session:closed"
    _start(gateway, session)
    gateway.sessions.complete(session)

    with pytest.raises(ValueError, match="OPEN WorkSession"):
        gateway.fetch("https://example.test/spec", session_id=session)

    assert calls == []


def test_gateway_binds_exact_capture_to_canonical_work_session_without_reliance(monkeypatch, tmp_path):
    body = b"gateway content"

    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(locator, locator, "captured", body, {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    gateway = TestamurSourceGateway(tmp_path / "evidence.db")
    session = "tst:work-session:gateway"
    _start(gateway, session)

    result = gateway.fetch(
        "https://example.test/doc",
        session_id=session,
        actor={"agent_ref": "codex", "version": "test"},
    )

    assert result.revision is not None
    assert result.event_receipt is not None
    assert result.event_receipt["binding_state"] == "FETCHED"
    assert result.event_receipt["durable_reliance_implied"] is False
    candidates = gateway.sessions.list_candidates(session)
    assert len(candidates) == 1
    observations = gateway.sessions.observations(session, candidate_id=candidates[0].candidate_id)
    assert [item.usage_state for item in observations] == [
        UsageState.DISCOVERED,
        UsageState.FETCHED,
    ]
    assert observations[-1].source_revision_id == result.revision["revision_id"]
    assert all(item.usage_state is not UsageState.RELIED_ON_BY_PROJECT_OBJECT for item in observations)


def test_gateway_unavailable_session_capture_records_discovery_not_fetch(monkeypatch, tmp_path):
    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(locator, locator, "unavailable", None, {"error": {"kind": "offline"}})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    gateway = TestamurSourceGateway(tmp_path / "evidence.db")
    session = "tst:work-session:unavailable"
    _start(gateway, session)

    result = gateway.fetch("https://example.test/offline", session_id=session)

    assert result.revision is None
    assert result.event_receipt["binding_state"] == "DISCOVERED_ONLY"
    candidate = gateway.sessions.list_candidates(session)[0]
    observations = gateway.sessions.observations(session, candidate_id=candidate.candidate_id)
    assert [item.usage_state for item in observations] == [UsageState.DISCOVERED]


def test_gateway_revalidate_tracks_new_revision(monkeypatch, tmp_path):
    payloads = iter([b"v1", b"v2"])

    def fake_fetch(locator, *, policy=None):
        body = next(payloads)
        return SourceFetchResult(locator, locator, "captured", body, {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    gateway = TestamurSourceGateway(tmp_path / "evidence.db")
    first = gateway.fetch("https://example.test/spec")
    second = gateway.revalidate(first.source["source_id"])

    assert first.revision["revision_id"] != second.revision["revision_id"]
    comparison = gateway.sources.compare_snapshots(
        first.snapshot["snapshot_id"], second.snapshot["snapshot_id"]
    )
    assert comparison["content_changed"] is True


def test_gateway_cli_source_status_is_machine_readable(monkeypatch, tmp_path, capsys):
    body = b"hello"

    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(locator, locator, "captured", body, {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    db = tmp_path / "evidence.db"
    gateway = TestamurSourceGateway(db)
    capture = gateway.fetch("https://example.test/a")

    code = gateway_main(["--db", str(db), "source-status", capture.source["source_id"]])
    assert code == 0
    value = json.loads(capsys.readouterr().out)
    assert value["schema"] == "testamur.source-gateway.status.v1"
    assert value["latest_revision"]["revision_id"] == capture.revision["revision_id"]
    assert value["blob"]["available"] is True
