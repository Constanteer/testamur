from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.agent_capture import AgentCapture
from testamur.agent_protocol import CanonicalSourceRevisionResolver
from testamur.assessment import PolicyEngine
from testamur.policy import PolicyStore
from testamur.reconciliation import ReconciliationDeclaration, reconcile_session
from testamur.reliance import RelianceStore
from testamur.reliance_bridge import CallbackEvidenceView, WorkSessionRelianceSink
from testamur.source_store import TestamurSourceStore
from testamur.work_session import (
    EvidenceClass,
    ReconciliationPolicy,
    RelianceDecision,
    UsageState,
    WorkSessionStatus,
    WorkSessionStore,
)


class ReleaseWorkSessionRelianceE2ETest(unittest.TestCase):
    def test_observed_exposed_reconciled_exact_reliance_then_change_has_blast_radius(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            source = sources.get_or_create_source("https://example.test/spec")
            first = sources.record_snapshot(
                source["source_id"],
                content=b"retry = 3\n",
                observed_at="2026-09-17T01:00:00Z",
            )

            def current_revision(object_ref: str) -> str | None:
                snapshot = sources.latest_recorded_snapshot(object_ref)
                return None if snapshot is None else snapshot.get("revision_id")

            evidence = CallbackEvidenceView(
                object_state=lambda ref: {**sources.get_source(ref), "kind": "source.web"},
                revision_ref=current_revision,
                assurances_for=lambda _ref: (
                    {
                        "assurance_id": "tst:verification:source-capture",
                        "assurance_kind": "mechanical.capture",
                        "status": "passed",
                        "recorded_at": "2026-09-17T01:00:00Z",
                    },
                ),
                outgoing_relations=lambda _ref: (),
                incoming_relations=lambda _ref: (),
            )
            policies = PolicyStore(db)
            policies.register(
                scope_ref="project:testamur",
                purpose="implement_retry_behavior",
                target_kind="source.web",
                definition={"required_assurances": ["mechanical.capture"]},
            )
            engine = PolicyEngine(policies, evidence)
            reliance = RelianceStore(db, engine)
            sink = WorkSessionRelianceSink(
                reliance,
                source_object_ref_for_revision=CanonicalSourceRevisionResolver(sources),
            )

            work = WorkSessionStore(root / "work.sqlite3")
            session = work.start_session(
                initiating_actor_ref="human:hank",
                host_environment="codex",
                project_ref="project:testamur",
                reconciliation_policy=ReconciliationPolicy.TRUST_AGENT_DECLARATION,
            )
            capture = AgentCapture(work)
            candidate = capture.discover(
                session.session_id,
                locator="https://example.test/spec",
                title="Retry specification",
            )
            capture.fetched(
                session.session_id,
                candidate.candidate_id,
                source_revision_id=first["revision_id"],
                retrieval_receipt_ref=first["snapshot_id"],
            )
            capture.expose_to_model(
                session.session_id,
                candidate.candidate_id,
                source_revision_id=first["revision_id"],
                generation_or_step_id="step:42",
                evidence_refs=("region:retry",),
                context_role="tool_result",
            )
            work.complete(session.session_id)

            report = reconcile_session(
                work,
                session.session_id,
                (
                    ReconciliationDeclaration(
                        candidate_id=candidate.candidate_id,
                        source_revision_id=first["revision_id"],
                        used=RelianceDecision.YES,
                        evidence_class=EvidenceClass.AGENT_DECLARED,
                        relation_type="depends_on",
                        used_for="implement_retry_behavior",
                        project_object_ref="artifact:client-patch",
                        exact_region_refs=("region:retry",),
                    ),
                ),
                actor_ref="agent:codex",
                reliance_sink=sink,
            )

            self.assertIs(report.status, WorkSessionStatus.RECONCILED)
            self.assertEqual(len(report.watch_candidates), 1)
            decisions = work.decisions(session.session_id)
            self.assertEqual(len(decisions), 1)
            self.assertIs(decisions[0].used, RelianceDecision.YES)
            self.assertIn(
                UsageState.RELIED_ON_BY_PROJECT_OBJECT,
                [
                    item.usage_state
                    for item in work.observations(
                        session.session_id, candidate_id=candidate.candidate_id
                    )
                ],
            )

            receipts = reliance.list(
                scope_ref="project:testamur", reliant_ref="artifact:client-patch"
            )
            self.assertEqual(len(receipts), 1)
            receipt = receipts[0]
            self.assertEqual(receipt["object_ref"], source["source_id"])
            self.assertEqual(
                receipt["pinned_revisions"][source["source_id"]], first["revision_id"]
            )
            self.assertFalse(receipt["semantics"]["exposure_implies_reliance"])

            second = sources.record_snapshot(
                source["source_id"],
                content=b"retry = 5\n",
                observed_at="2026-09-17T02:00:00Z",
            )
            self.assertNotEqual(second["revision_id"], first["revision_id"])

            verification = reliance.verify(receipt["receipt_id"])
            self.assertTrue(verification["stale"])
            revision_reasons = [
                reason
                for reason in verification["staleness_reasons"]
                if reason["type"] == "object_revision_changed"
            ]
            self.assertEqual(
                revision_reasons,
                [
                    {
                        "type": "object_revision_changed",
                        "object_ref": source["source_id"],
                        "was": first["revision_id"],
                        "now": second["revision_id"],
                    }
                ],
            )
            self.assertFalse(verification["semantics"]["staleness_implies_false"])
            self.assertFalse(verification["semantics"]["change_implies_invalidity"])

            impact = reliance.blast_radius(
                scope_ref="project:testamur",
                changed_object_refs=[source["source_id"]],
            )
            self.assertEqual(impact["affected_reliant_refs"], ["artifact:client-patch"])
            self.assertEqual(impact["affected_receipt_count"], 1)
            self.assertTrue(impact["affected_receipts"][0]["currently_stale"])
            self.assertFalse(impact["semantics"]["change_implies_false"])


if __name__ == "__main__":
    unittest.main()
