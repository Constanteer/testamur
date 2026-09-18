from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, Iterable, Mapping

from testamur.assessment import PolicyEngine
from testamur.policy import PolicyStore


class _Evidence:
    """One immutable evidence view evaluated under multiple explicit policies."""

    def __init__(self) -> None:
        self._object = {"kind": "artifact", "state": "recorded"}
        self._revision = "tst:revision:" + "a" * 64
        self._assurances = [
            {
                "assurance_id": "tst:verification:fixture",
                "assurance_kind": "mechanical.check",
                "status": "passed",
                "scope": {"runner": "local"},
                "recorded_at": "2026-09-17T00:00:00Z",
            }
        ]

    def object_state(self, object_ref: str) -> Mapping[str, Any]:
        return dict(self._object)

    def revision_ref(self, object_ref: str) -> str | None:
        return self._revision

    def assurances_for(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return [dict(item) for item in self._assurances]

    def outgoing_relations(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return []

    def incoming_relations(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return []


class ReleasePolicyContextE2ETest(unittest.TestCase):
    def test_same_evidence_can_have_different_explainable_policy_assessments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PolicyStore(Path(tmp) / "testamur.sqlite3")
            evidence = _Evidence()
            engine = PolicyEngine(store, evidence)
            object_ref = "tst:record:fixture"

            permissive = store.register(
                scope_ref="scope:release",
                purpose="release.use",
                target_kind="artifact",
                definition={
                    "required_assurances": ["mechanical.check"],
                    "assurance_scope_requirements": {
                        "mechanical.check": {"runner": "local"}
                    },
                },
            )
            strict = store.register(
                scope_ref="scope:regulated",
                purpose="release.use",
                target_kind="artifact",
                definition={
                    "required_assurances": ["mechanical.check", "human.review"],
                    "assurance_scope_requirements": {
                        "mechanical.check": {"runner": "local"}
                    },
                },
            )

            accepted = engine.evaluate(
                scope_ref="scope:release", object_ref=object_ref, purpose="release.use"
            )
            rejected = engine.evaluate(
                scope_ref="scope:regulated", object_ref=object_ref, purpose="release.use"
            )

            self.assertTrue(accepted["admissible"])
            self.assertEqual(accepted["assessment_state"], "SUPPORTED")
            self.assertFalse(rejected["admissible"])
            self.assertEqual(rejected["assessment_state"], "UNVERIFIED")
            self.assertEqual(
                rejected["blockers"],
                [
                    {
                        "type": "missing_assurance",
                        "object_ref": object_ref,
                        "assurance_kind": "human.review",
                    }
                ],
            )

            # The evidence and exact revision are unchanged. Only the explicit
            # policy context differs; policy evaluation must not mutate evidence.
            self.assertEqual(accepted["object_revision_ref"], rejected["object_revision_ref"])
            self.assertEqual(evidence._assurances[0]["status"], "passed")
            self.assertEqual(accepted["policy"]["policy_id"], permissive["policy_id"])
            self.assertEqual(rejected["policy"]["policy_id"], strict["policy_id"])
            self.assertFalse(accepted["semantics"]["evidence_implies_truth"])
            self.assertFalse(rejected["semantics"]["evidence_implies_truth"])
            self.assertIsNone(accepted["semantics"]["universal_trust_score"])


if __name__ == "__main__":
    unittest.main()
