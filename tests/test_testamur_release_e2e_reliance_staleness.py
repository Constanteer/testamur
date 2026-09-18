from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.assessment import PolicyEngine
from testamur.policy import PolicyStore
from testamur.policy_evidence import RecordPolicyEvidenceView
from testamur.record_store import TestamurRecordStore
from testamur.reliance import RelianceStore


class ReleaseRelianceStalenessE2ETest(unittest.TestCase):
    def test_upstream_revision_change_makes_exact_downstream_reliance_stale_not_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "testamur.sqlite3"
            records = TestamurRecordStore(db)
            policies = PolicyStore(db)

            upstream = records.create_record(
                record_kind="source.fact", statement="upstream revision one"
            )
            downstream = records.create_record(
                record_kind="build.result", statement="release candidate"
            )
            relation = records.create_relation(
                "depends-on",
                from_ref=downstream["record"]["record_id"],
                to_ref=upstream["record"]["record_id"],
                basis=[{"kind": "declared", "ref": "fixture:dependency"}],
            )

            assurances = {
                upstream["record"]["record_id"]: [
                    {
                        "assurance_id": "tst:verification:upstream",
                        "assurance_kind": "mechanical.check",
                        "status": "passed",
                        "recorded_at": "2026-09-17T00:00:00Z",
                    }
                ],
                downstream["record"]["record_id"]: [
                    {
                        "assurance_id": "tst:verification:downstream",
                        "assurance_kind": "mechanical.check",
                        "status": "passed",
                        "recorded_at": "2026-09-17T00:00:00Z",
                    }
                ],
            }
            evidence = RecordPolicyEvidenceView(
                records, assurance_reader=lambda ref: assurances.get(ref, [])
            )
            for kind in ("source.fact", "build.result"):
                policies.register(
                    scope_ref="scope:release",
                    purpose="release.use",
                    target_kind=kind,
                    definition={
                        "required_assurances": ["mechanical.check"],
                        "dependency_relation_types": ["depends-on"],
                        "require_dependencies_admissible": True,
                    },
                )

            engine = PolicyEngine(policies, evidence)
            reliance = RelianceStore(db, engine)
            receipt = reliance.issue(
                scope_ref="scope:release",
                reliant_ref="project:consumer",
                reliant_revision_ref="project:consumer@rev1",
                object_ref=downstream["record"]["record_id"],
                purpose="release.use",
            )

            self.assertFalse(receipt["stale"])
            self.assertEqual(
                receipt["pinned_revisions"][upstream["record"]["record_id"]],
                upstream["revision"]["revision_id"],
            )
            self.assertIn(relation["relation_id"], receipt["relation_ids"])

            next_upstream = records.append_revision(
                upstream["record"]["record_id"],
                expected_parent_revision_id=upstream["revision"]["revision_id"],
                statement="upstream revision two",
            )
            current = reliance.verify(receipt["receipt_id"])

            self.assertTrue(current["stale"])
            revision_reasons = [
                reason
                for reason in current["staleness_reasons"]
                if reason["type"] == "object_revision_changed"
            ]
            self.assertEqual(len(revision_reasons), 1)
            self.assertEqual(
                revision_reasons[0],
                {
                    "type": "object_revision_changed",
                    "object_ref": upstream["record"]["record_id"],
                    "was": upstream["revision"]["revision_id"],
                    "now": next_upstream["revision_id"],
                },
            )
            self.assertFalse(current["semantics"]["staleness_implies_false"])
            self.assertFalse(current["semantics"]["change_implies_invalidity"])

            impact = reliance.blast_radius(
                scope_ref="scope:release",
                changed_object_refs=[upstream["record"]["record_id"]],
            )
            self.assertEqual(impact["affected_reliant_refs"], ["project:consumer"])
            self.assertEqual(impact["affected_receipt_count"], 1)
            self.assertTrue(impact["affected_receipts"][0]["currently_stale"])
            self.assertFalse(impact["semantics"]["change_implies_false"])


if __name__ == "__main__":
    unittest.main()
