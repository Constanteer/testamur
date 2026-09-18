from __future__ import annotations

from dataclasses import dataclass

import pytest

from testamur.agent_capture import AgentCapture
from testamur.agent_protocol import (
    RelianceCommitRequest,
    RelianceCommitResult,
    WatchRegistrationRequest,
    WatchRegistrationResult,
)
from testamur.reconciliation import (
    ReconciliationDeclaration,
    prepare_reconciliation,
    reconcile_session,
)
from testamur.work_session import (
    EvidenceClass,
    ReconciliationPolicy,
    RelianceDecision,
    UsageState,
    WorkSessionStatus,
    WorkSessionStore,
)


@dataclass
class FakeRelianceSink:
    requests: list[RelianceCommitRequest]

    def commit_reliance(self, request: RelianceCommitRequest) -> RelianceCommitResult:
        self.requests.append(request)
        return RelianceCommitResult(reliance_id=f"tst:reliance:{len(self.requests)}")


@dataclass
class FakeWatchSink:
    requests: list[WatchRegistrationRequest]

    def register_watch(self, request: WatchRegistrationRequest) -> WatchRegistrationResult:
        self.requests.append(request)
        return WatchRegistrationResult(watch_ref=f"tst:watch:{len(self.requests)}")


def build_completed_session(tmp_path, *, policy=ReconciliationPolicy.TRUST_AGENT_DECLARATION):
    store = WorkSessionStore(tmp_path / "work.db")
    session = store.start_session(
        initiating_actor_ref="human:hank",
        host_environment="codex",
        project_ref="project:testamur",
        reconciliation_policy=policy,
    )
    capture = AgentCapture(store)
    used = capture.discover(session.session_id, locator="https://example.test/api", title="API")
    capture.fetched(
        session.session_id,
        used.candidate_id,
        source_revision_id="tst:revision:api-v7",
        retrieval_receipt_ref="receipt:api-v7",
    )
    capture.expose_to_model(
        session.session_id,
        used.candidate_id,
        source_revision_id="tst:revision:api-v7",
        generation_or_step_id="step:42",
        evidence_refs=("region:retry",),
        context_role="tool_result",
    )
    unused = capture.discover(session.session_id, locator="https://example.test/blog", title="Blog")
    capture.fetched(
        session.session_id,
        unused.candidate_id,
        source_revision_id="tst:revision:blog-v1",
        retrieval_receipt_ref="receipt:blog-v1",
    )
    store.complete(session.session_id)
    return store, session.session_id, used, unused


def test_session_observe_reconcile_reliance_watch_e2e(tmp_path):
    store, session_id, used, unused = build_completed_session(tmp_path)
    inputs = prepare_reconciliation(store, session_id)
    assert {(i.candidate_id, i.source_revision_id) for i in inputs} == {
        (used.candidate_id, "tst:revision:api-v7"),
        (unused.candidate_id, "tst:revision:blog-v1"),
    }

    reliance = FakeRelianceSink([])
    watch = FakeWatchSink([])
    report = reconcile_session(
        store,
        session_id,
        (
            ReconciliationDeclaration(
                candidate_id=used.candidate_id,
                source_revision_id="tst:revision:api-v7",
                used=RelianceDecision.YES,
                evidence_class=EvidenceClass.AGENT_DECLARED,
                relation_type="depends_on",
                used_for="retry behavior in src/client.py",
                project_object_ref="artifact:client-patch",
                exact_region_refs=("region:retry",),
            ),
            ReconciliationDeclaration(
                candidate_id=unused.candidate_id,
                source_revision_id="tst:revision:blog-v1",
                used=RelianceDecision.NO,
                evidence_class=EvidenceClass.AGENT_DECLARED,
                notes="inspected but not used",
            ),
        ),
        actor_ref="agent:codex",
        reliance_sink=reliance,
        watch_sink=watch,
    )

    assert report.status is WorkSessionStatus.RECONCILED
    assert len(reliance.requests) == 1
    request = reliance.requests[0]
    assert request.source_revision_id == "tst:revision:api-v7"
    assert request.project_object_ref == "artifact:client-patch"
    assert request.reconciliation_policy == ReconciliationPolicy.TRUST_AGENT_DECLARATION.value
    assert len(report.watch_candidates) == 1
    assert report.watch_candidates[0].source_revision_id == "tst:revision:api-v7"
    assert len(watch.requests) == 1

    used_states = [
        o.usage_state
        for o in store.observations(session_id, candidate_id=used.candidate_id)
    ]
    unused_states = [
        o.usage_state
        for o in store.observations(session_id, candidate_id=unused.candidate_id)
    ]
    assert UsageState.RELIED_ON_BY_PROJECT_OBJECT in used_states
    assert UsageState.RELIED_ON_BY_PROJECT_OBJECT not in unused_states


def test_no_sink_leaves_session_unreconciled_and_can_resume_idempotently(tmp_path):
    store, session_id, used, unused = build_completed_session(tmp_path)
    declarations = (
        ReconciliationDeclaration(
            candidate_id=used.candidate_id,
            source_revision_id="tst:revision:api-v7",
            used=RelianceDecision.YES,
            evidence_class=EvidenceClass.AGENT_DECLARED,
            relation_type="depends_on",
            used_for="retry behavior",
            project_object_ref="artifact:patch",
        ),
        ReconciliationDeclaration(
            candidate_id=unused.candidate_id,
            source_revision_id="tst:revision:blog-v1",
            used=RelianceDecision.UNCERTAIN,
            evidence_class=EvidenceClass.AGENT_DECLARED,
        ),
    )
    first = reconcile_session(
        store,
        session_id,
        declarations,
        actor_ref="agent:codex",
        reliance_sink=None,
    )
    assert first.status is WorkSessionStatus.COMPLETED_UNRECONCILED
    assert len(first.pending_reliance_decision_ids) == 1
    assert store.watch_candidates(session_id) == []

    sink = FakeRelianceSink([])
    second = reconcile_session(
        store,
        session_id,
        declarations,
        actor_ref="agent:codex",
        reliance_sink=sink,
    )
    assert second.status is WorkSessionStatus.RECONCILED
    assert len(sink.requests) == 1
    assert len(store.decisions(session_id)) == 2

    third = reconcile_session(
        store,
        session_id,
        declarations,
        actor_ref="agent:codex",
        reliance_sink=sink,
    )
    assert third.status is WorkSessionStatus.RECONCILED
    assert len(sink.requests) == 1


def test_reconciliation_must_cover_every_observed_input(tmp_path):
    store, session_id, used, unused = build_completed_session(tmp_path)
    with pytest.raises(ValueError, match="cover every observed input"):
        reconcile_session(
            store,
            session_id,
            (
                ReconciliationDeclaration(
                    candidate_id=used.candidate_id,
                    source_revision_id="tst:revision:api-v7",
                    used=RelianceDecision.NO,
                    evidence_class=EvidenceClass.AGENT_DECLARED,
                ),
            ),
            actor_ref="agent:codex",
            reliance_sink=None,
        )


def test_human_confirmation_policy_rejects_agent_only_commitment(tmp_path):
    store, session_id, used, unused = build_completed_session(
        tmp_path, policy=ReconciliationPolicy.ASK_USER_TO_CONFIRM
    )
    with pytest.raises(ValueError, match="HUMAN_CONFIRMED"):
        reconcile_session(
            store,
            session_id,
            (
                ReconciliationDeclaration(
                    candidate_id=used.candidate_id,
                    source_revision_id="tst:revision:api-v7",
                    used=RelianceDecision.YES,
                    evidence_class=EvidenceClass.AGENT_DECLARED,
                    relation_type="depends_on",
                    used_for="retry",
                    project_object_ref="artifact:patch",
                ),
                ReconciliationDeclaration(
                    candidate_id=unused.candidate_id,
                    source_revision_id="tst:revision:blog-v1",
                    used=RelianceDecision.NO,
                    evidence_class=EvidenceClass.HUMAN_CONFIRMED,
                ),
            ),
            actor_ref="human:hank",
            reliance_sink=FakeRelianceSink([]),
        )


def test_discovered_only_input_cannot_be_relied_on_without_exact_revision(tmp_path):
    store = WorkSessionStore(tmp_path / "work.db")
    session = store.start_session(
        initiating_actor_ref="human:hank",
        host_environment="codex",
    )
    candidate = AgentCapture(store).discover(
        session.session_id, locator="https://example.test/search-result"
    )
    store.complete(session.session_id)
    with pytest.raises(ValueError, match="discovered-only"):
        reconcile_session(
            store,
            session.session_id,
            (
                ReconciliationDeclaration(
                    candidate_id=candidate.candidate_id,
                    source_revision_id=None,
                    used=RelianceDecision.YES,
                    evidence_class=EvidenceClass.AGENT_DECLARED,
                    relation_type="depends_on",
                    used_for="something",
                    project_object_ref="artifact:x",
                ),
            ),
            actor_ref="agent:codex",
            reliance_sink=FakeRelianceSink([]),
        )


def test_invalid_late_declaration_does_not_persist_partial_decisions(tmp_path):
    store, session_id, used, unused = build_completed_session(tmp_path)
    with pytest.raises(ValueError, match="used=yes requires project_object_ref"):
        reconcile_session(
            store,
            session_id,
            (
                ReconciliationDeclaration(
                    candidate_id=used.candidate_id,
                    source_revision_id="tst:revision:api-v7",
                    used=RelianceDecision.NO,
                    evidence_class=EvidenceClass.AGENT_DECLARED,
                ),
                ReconciliationDeclaration(
                    candidate_id=unused.candidate_id,
                    source_revision_id="tst:revision:blog-v1",
                    used=RelianceDecision.YES,
                    evidence_class=EvidenceClass.AGENT_DECLARED,
                    relation_type="depends_on",
                    used_for="bad incomplete declaration",
                    project_object_ref=None,
                ),
            ),
            actor_ref="agent:codex",
            reliance_sink=FakeRelianceSink([]),
        )
    assert store.decisions(session_id) == []
    assert store.get_reconciliation(session_id) is None


def test_disabled_policy_remains_archive_only(tmp_path):
    store, session_id, used, unused = build_completed_session(
        tmp_path, policy=ReconciliationPolicy.DISABLED
    )
    assert prepare_reconciliation(store, session_id)
    with pytest.raises(ValueError, match="disabled reconciliation"):
        reconcile_session(
            store,
            session_id,
            (),
            actor_ref="agent:codex",
            reliance_sink=None,
        )
    assert store.get_session(session_id).status is WorkSessionStatus.COMPLETED_UNRECONCILED
    assert store.get_reconciliation(session_id) is None


def test_exact_revision_mismatch_cannot_be_exposed(tmp_path):
    store = WorkSessionStore(tmp_path / "work.db")
    session = store.start_session(
        initiating_actor_ref="human:hank", host_environment="codex"
    )
    capture = AgentCapture(store)
    candidate = capture.discover(session.session_id, locator="https://example.test/spec")
    capture.fetched(
        session.session_id, candidate.candidate_id,
        source_revision_id="tst:revision:r1", retrieval_receipt_ref="receipt:r1",
    )
    with pytest.raises(ValueError, match="prior FETCHED/INSPECTED"):
        capture.expose_to_model(
            session.session_id, candidate.candidate_id,
            source_revision_id="tst:revision:r2", generation_or_step_id="step:1",
            evidence_refs=("region:r2",),
        )


def test_operational_lane_projection_separates_watch_archive_pending(tmp_path):
    from testamur.reconciliation import project_operational_lanes

    store, session_id, used, unused = build_completed_session(tmp_path)
    declarations = (
        ReconciliationDeclaration(
            candidate_id=used.candidate_id,
            source_revision_id="tst:revision:api-v7",
            used=RelianceDecision.YES,
            evidence_class=EvidenceClass.AGENT_DECLARED,
            relation_type="depends_on",
            used_for="retry behavior",
            project_object_ref="artifact:patch",
        ),
        ReconciliationDeclaration(
            candidate_id=unused.candidate_id,
            source_revision_id="tst:revision:blog-v1",
            used=RelianceDecision.NO,
            evidence_class=EvidenceClass.AGENT_DECLARED,
        ),
    )
    reconcile_session(
        store, session_id, declarations,
        actor_ref="agent:codex", reliance_sink=None,
    )
    lanes = project_operational_lanes(store, session_id)
    assert lanes.watch == ()
    assert len(lanes.archive) == 1
    assert lanes.archive[0].candidate_id == unused.candidate_id
    assert len(lanes.pending_reliance_decision_ids) == 1
    assert lanes.unreconciled_inputs == ()

    reconcile_session(
        store, session_id, declarations,
        actor_ref="agent:codex", reliance_sink=FakeRelianceSink([]),
    )
    lanes = project_operational_lanes(store, session_id)
    assert len(lanes.watch) == 1
    assert len(lanes.archive) == 1
    assert lanes.pending_reliance_decision_ids == ()
    assert lanes.unreconciled_inputs == ()
