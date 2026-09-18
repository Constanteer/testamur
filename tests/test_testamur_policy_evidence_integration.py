from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.assessment import PolicyEngine
from testamur.policy import PolicyStore
from testamur.policy_evidence import RecordPolicyEvidenceView
from testamur.record_store import TestamurRecordStore


class RecordPolicyEvidenceIntegrationTest(unittest.TestCase):
    def test_policy_traverses_canonical_record_relations_without_rewriting_graph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "testamur.sqlite3"
            records = TestamurRecordStore(db)
            policies = PolicyStore(db)

            source = records.create_record(
                record_kind="source.fact", statement="upstream fixture"
            )
            result = records.create_record(
                record_kind="build.result", statement="downstream fixture"
            )
            relation = records.create_relation(
                "depends-on",
                from_ref=result["record"]["record_id"],
                to_ref=source["record"]["record_id"],
                basis=[{"kind": "declared", "ref": "fixture:test"}],
            )

            assurances = {
                source["record"]["record_id"]: [
                    {
                        "assurance_id": "tst:verification:source",
                        "assurance_kind": "mechanical.check",
                        "status": "passed",
                        "recorded_at": "2026-09-17T00:00:00Z",
                    }
                ],
                result["record"]["record_id"]: [
                    {
                        "assurance_id": "tst:verification:result",
                        "assurance_kind": "mechanical.check",
                        "status": "passed",
                        "recorded_at": "2026-09-17T00:00:00Z",
                    }
                ],
            }
            view = RecordPolicyEvidenceView(
                records, assurance_reader=lambda ref: assurances.get(ref, [])
            )
            engine = PolicyEngine(policies, view)

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

            decision = engine.evaluate(
                scope_ref="scope:release",
                object_ref=result["record"]["record_id"],
                purpose="release.use",
            )
            self.assertTrue(decision["admissible"])
            self.assertEqual(decision["assessment_state"], "SUPPORTED")
            self.assertEqual(
                decision["object_revision_ref"], result["revision"]["revision_id"]
            )
            self.assertEqual(len(decision["dependencies"]), 1)
            self.assertEqual(
                decision["dependencies"][0]["relation"]["relation_id"],
                relation["relation_id"],
            )
            self.assertEqual(
                decision["dependencies"][0]["state"]["object_revision_ref"],
                source["revision"]["revision_id"],
            )
            self.assertFalse(
                view.object_state(result["record"]["record_id"])["semantics"][
                    "recorded_is_verified"
                ]
            )

    def test_recording_without_assurance_remains_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "testamur.sqlite3"
            records = TestamurRecordStore(db)
            policies = PolicyStore(db)
            created = records.create_record(record_kind="artifact", statement="recorded only")
            policies.register(
                scope_ref="scope:release",
                purpose="release.use",
                target_kind="artifact",
                definition={"required_assurances": ["mechanical.check"]},
            )
            decision = PolicyEngine(
                policies, RecordPolicyEvidenceView(records)
            ).evaluate(
                scope_ref="scope:release",
                object_ref=created["record"]["record_id"],
                purpose="release.use",
            )
            self.assertFalse(decision["admissible"])
            self.assertEqual(decision["assessment_state"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
