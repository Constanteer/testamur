from __future__ import annotations

from testamur._work_session_types import EvidenceClass, RelianceDecision
from testamur.agent_protocol import (
    CanonicalWatchSink,
    RelianceCommitResult,
)
from testamur.reconciliation import ReconciliationDeclaration, reconcile_session
from testamur.runtime_protocol import canonical_hash
from testamur.source_fetch import SourceFetchResult
from testamur.source_gateway import TestamurSourceGateway


class _RelianceSink:
    def commit_reliance(self, request):
        return RelianceCommitResult(
            reliance_id="tst:reliance:" + canonical_hash({"decision_id": request.decision_id})
        )


def test_exact_gateway_capture_reconciles_into_canonical_watch_and_refresh(monkeypatch, tmp_path):
    payloads = iter([b"spec-v1", b"spec-v2"])

    def fake_fetch(locator, *, policy=None):
        body = next(payloads)
        return SourceFetchResult(
            requested_locator=locator,
            final_locator=locator,
            status="captured",
            content=body,
            metadata={"status_code": 200, "content_type": "text/plain"},
        )

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    gateway = TestamurSourceGateway(tmp_path / "evidence.db")
    session_id = "tst:work-session:e2e"
    gateway.sessions.start_session(
        initiating_actor_ref="test:actor",
        host_environment="pytest",
        project_ref="tst:project:e2e",
        agent_ref="codex",
        agent_version="test",
        session_id=session_id,
    )

    first = gateway.fetch(
        "https://example.test/spec",
        session_id=session_id,
        actor={"agent_ref": "codex", "version": "test"},
    )
    assert first.revision is not None
    candidate = gateway.sessions.list_candidates(session_id)[0]
    gateway.sessions.complete(session_id)

    report = reconcile_session(
        gateway.sessions,
        session_id,
        [
            ReconciliationDeclaration(
                candidate_id=candidate.candidate_id,
                source_revision_id=first.revision["revision_id"],
                used=RelianceDecision.YES,
                evidence_class=EvidenceClass.AGENT_DECLARED,
                relation_type="depends_on",
                used_for="implement retry semantics",
                project_object_ref="src/client.py",
            )
        ],
        actor_ref="test:reconciler",
        reliance_sink=_RelianceSink(),
        watch_sink=CanonicalWatchSink(gateway.sources, gateway.watches),
    )

    assert report.exports_complete is True
    assert len(report.watch_candidates) == 1
    watch_candidate = report.watch_candidates[0]
    watch_ref = gateway.sessions.external_watch_ref(watch_candidate.watch_candidate_id)
    assert watch_ref is not None

    baseline = gateway.watches.evaluate_snapshot(
        gateway.sources,
        watch_id=watch_ref,
        snapshot_id=first.snapshot["snapshot_id"],
    )
    assert baseline["evaluation"]["operational_state"] == "initial"

    refreshed = gateway.refresh_watch(watch_ref)
    assert refreshed["evaluation"]["operational_state"] == "changed"
    assert refreshed["alert"] is not None
    assert refreshed["alert"]["event_type"] == "changed"
    assert refreshed["semantics"]["downstream_invalidity_implied"] is False
