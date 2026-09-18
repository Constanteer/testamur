from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from testamur._work_session_types import (
    EvidenceClass,
    ReconciliationPolicy,
    RelianceDecision,
    UsageState,
    WorkSessionStatus,
)
from testamur.assessment import PolicyEngine
from testamur.policy import PolicyStore
from testamur.reliance import RelianceStore
from testamur.work_session import WorkSessionStore


class MutableEvidence:
    def __init__(self) -> None:
        self.revisions = {"source:upstream": "tst:revision:upstream:v1"}

    def object_state(self, object_ref: str) -> Mapping[str, Any]:
        if object_ref not in self.revisions:
            raise KeyError(object_ref)
        return {"kind": "source", "state": "recorded"}

    def revision_ref(self, object_ref: str) -> str | None:
        return self.revisions[object_ref]

    def assurances_for(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return ()

    def outgoing_relations(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return ()

    def incoming_relations(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return ()


def test_gate_b_exposure_reconciles_to_exact_reliance_then_blast_radius(tmp_path: Path) -> None:
    db = tmp_path / "testamur.sqlite3"
    scope = "project:fixture"
    evidence = MutableEvidence()
    policies = PolicyStore(db)
    policies.register(
        scope_ref=scope,
        purpose="build",
        target_kind="source",
        definition={
            "required_assurances": [],
            "dependency_relation_types": [],
            "blocking_relation_types": [],
            "require_dependencies_admissible": False,
        },
    )
    reliance = RelianceStore(db, PolicyEngine(policies, evidence))

    with WorkSessionStore(db) as work:
        session = work.start_session(
            initiating_actor_ref="agent:test",
            host_environment="fixture",
            project_ref=scope,
            reconciliation_policy=ReconciliationPolicy.TRUST_AGENT_DECLARATION,
        )
        candidate = work.create_candidate(session.session_id, locator="https://example.invalid/upstream")
        fetched = work.record_observation(
            session.session_id,
            candidate.candidate_id,
            UsageState.FETCHED,
            source_revision_id="tst:revision:upstream:v1",
            evidence_refs=["fetch:receipt:1"],
        )
        work.record_observation(
            session.session_id,
            candidate.candidate_id,
            UsageState.EXPOSED_TO_MODEL,
            source_revision_id="tst:revision:upstream:v1",
            evidence_refs=[fetched.observation_id, "model:context:1"],
        )
        assert UsageState.RELIED_ON_BY_PROJECT_OBJECT not in {
            item.usage_state for item in work.observations(session.session_id)
        }

        work.complete(session.session_id)
        reconciliation = work.start_reconciliation(
            session.session_id,
            policy=ReconciliationPolicy.TRUST_AGENT_DECLARATION,
            actor_ref="agent:test",
        )
        decision = work.record_decision(
            reconciliation.reconciliation_id,
            candidate_id=candidate.candidate_id,
            source_revision_id="tst:revision:upstream:v1",
            used=RelianceDecision.YES,
            evidence_class=EvidenceClass.AGENT_DECLARED,
            relation_type="relied_on",
            used_for="build",
            project_object_ref="artifact:downstream",
            evidence_refs=["model:context:1"],
        )

        receipt = reliance.issue(
            scope_ref=scope,
            reliant_ref="artifact:downstream",
            reliant_revision_ref="artifact-revision:downstream:v1",
            object_ref="source:upstream",
            purpose="build",
        )
        assert receipt["pinned_revisions"]["source:upstream"] == "tst:revision:upstream:v1"
        work.record_reliance_export(decision.decision_id, reliance_id=receipt["receipt_id"])
        watch_candidate = work.ensure_watch_candidate(decision.decision_id)
        assert watch_candidate.source_revision_id == "tst:revision:upstream:v1"
        assert watch_candidate.reliance_id == receipt["receipt_id"]
        reconciled = work.mark_reconciled_if_complete(session.session_id)
        assert reconciled.status is WorkSessionStatus.RECONCILED
        assert UsageState.RELIED_ON_BY_PROJECT_OBJECT in {
            item.usage_state for item in work.observations(session.session_id)
        }

    evidence.revisions["source:upstream"] = "tst:revision:upstream:v2"
    impact = reliance.blast_radius(
        scope_ref=scope,
        changed_object_refs=["source:upstream"],
    )
    assert impact["affected_receipt_count"] == 1
    assert impact["affected_reliant_refs"] == ["artifact:downstream"]
    affected = impact["affected_receipts"][0]
    assert affected["currently_stale"] is True

    checked = reliance.verify(receipt["receipt_id"])
    assert checked["stale"] is True
    assert any(
        reason["type"] == "object_revision_changed"
        and reason["was"] == "tst:revision:upstream:v1"
        and reason["now"] == "tst:revision:upstream:v2"
        for reason in checked["staleness_reasons"]
    )
