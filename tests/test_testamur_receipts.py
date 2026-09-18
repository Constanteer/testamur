from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from testamur.artifacts import snapshot_path
from testamur.receipt_store import TestamurReceiptStore


class TestamurReceiptStoreTest(unittest.TestCase):
    def make_receipt(self, root: Path) -> dict:
        input_path = root / "input.txt"
        output_path = root / "output.txt"
        input_path.write_text("alpha\n", encoding="utf-8")
        output_path.write_text("result\n", encoding="utf-8")
        return {
            "run_id": "tst:run:test-receipt",
            "state": "finished",
            "argv": ["python", "work.py"],
            "cwd": str(root),
            "exit_code": 0,
            "record_digest": "sha256:runtime-record",
            "verification_implied": False,
            "replayed": False,
            "git_context": {
                "before": {"status": "not_repository"},
                "after": {"status": "not_repository"},
            },
            "worktree_delta": {"status": "disabled"},
            "input_artifacts": [
                {
                    "role": "input",
                    "declared_path": "input.txt",
                    "resolved_path": str(input_path),
                    "status": "captured",
                    "snapshot": snapshot_path(input_path, root=root),
                }
            ],
            "output_artifacts": [
                {
                    "role": "output",
                    "declared_path": "output.txt",
                    "resolved_path": str(output_path),
                    "status": "captured",
                    "snapshot": snapshot_path(output_path, root=root),
                }
            ],
        }

    def test_record_explain_and_impact_without_claiming_verification(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = TestamurReceiptStore(root / "testamur.sqlite3")
            receipt = self.make_receipt(root)
            recorded = store.record(receipt)
            self.assertEqual(recorded["artifact_observation_count"], 2)
            self.assertFalse(recorded["verification_implied"])

            explanation = store.explain("output.txt", root=root)
            self.assertEqual(explanation["kind"], "artifact")
            self.assertEqual(
                explanation["observed_as_declared_output"][0]["run_id"],
                receipt["run_id"],
            )
            self.assertFalse(explanation["causal_attribution_implied"])
            self.assertEqual(
                explanation["verification"],
                "not_inferred_from_artifact_observation",
            )

            unchanged = store.impact("input.txt", root=root)
            self.assertEqual(
                unchanged["consumers"][0]["state"],
                "input_matches_observation",
            )
            self.assertFalse(unchanged["semantics"]["change_implies_invalidation"])
            self.assertFalse(unchanged["semantics"]["causal_attribution_implied"])
            self.assertTrue(unchanged["semantics"]["impact_uses_persisted_observations"])

            (root / "input.txt").write_text("beta\n", encoding="utf-8")
            changed = store.impact("input.txt", root=root)
            self.assertEqual(
                changed["consumers"][0]["state"],
                "requires_revalidation",
            )
            self.assertEqual(
                changed["potentially_affected_observations"][0]["state"],
                "potentially_stale_requires_revalidation",
            )
            self.assertFalse(
                changed["potentially_affected_observations"][0]["causal_attribution_implied"]
            )

    def test_impact_uses_persisted_worktree_observations_not_live_resnapshot(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            input_path = root / "input.txt"
            changed_path = root / "changed.txt"
            input_path.write_text("before\n", encoding="utf-8")
            changed_path.write_text("captured\n", encoding="utf-8")
            store = TestamurReceiptStore(root / "testamur.sqlite3")
            receipt = {
                "run_id": "tst:run:persisted-impact",
                "state": "finished",
                "argv": ["agent", "edit"],
                "cwd": str(root),
                "exit_code": 0,
                "record_digest": "sha256:persisted-impact",
                "verification_implied": False,
                "replayed": False,
                "git_context": {"before": {}, "after": {}},
                "worktree_delta": {
                    "status": "captured",
                    "added": ["changed.txt"],
                    "changed": [],
                    "removed": [],
                },
                "input_artifacts": [
                    {
                        "role": "input",
                        "declared_path": "input.txt",
                        "resolved_path": str(input_path),
                        "status": "captured",
                        "snapshot": snapshot_path(input_path, root=root),
                    }
                ],
                "output_artifacts": [],
            }
            store.record(receipt)
            persisted = store.observations_for_run(receipt["run_id"])
            worktree = [item for item in persisted if item["role"] == "worktree_change"]
            self.assertEqual(len(worktree), 1)

            changed_path.write_text("later bytes\n", encoding="utf-8")
            input_path.write_text("changed input\n", encoding="utf-8")
            with patch.object(
                TestamurReceiptStore,
                "_worktree_observations",
                side_effect=AssertionError("impact must not resnapshot historical worktree state"),
            ):
                impact = store.impact("input.txt", root=root)

            affected = impact["potentially_affected_observations"]
            self.assertEqual(len(affected), 1)
            self.assertEqual(affected[0]["path"], "changed.txt")
            self.assertEqual(affected[0]["observation_role"], "worktree_change")
            self.assertEqual(affected[0]["observation_id"], worktree[0]["observation_id"])
            self.assertTrue(impact["semantics"]["impact_uses_persisted_observations"])

    def test_worktree_change_is_queryable_without_calling_it_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            changed_path = root / "changed.txt"
            changed_path.write_text("after\n", encoding="utf-8")
            store = TestamurReceiptStore(root / "testamur.sqlite3")
            receipt = {
                "run_id": "tst:run:worktree",
                "state": "finished",
                "argv": ["agent", "edit"],
                "cwd": str(root),
                "exit_code": 0,
                "record_digest": "sha256:worktree-run",
                "verification_implied": False,
                "replayed": False,
                "git_context": {"before": {}, "after": {}},
                "worktree_delta": {
                    "status": "captured",
                    "added": ["changed.txt"],
                    "changed": [],
                    "removed": [],
                    "before_digest": "sha256:before",
                    "after_digest": "sha256:after",
                },
                "input_artifacts": [],
                "output_artifacts": [],
            }
            recorded = store.record(receipt)
            self.assertEqual(recorded["artifact_observation_count"], 1)
            explanation = store.explain("changed.txt", root=root)
            self.assertEqual(explanation["observed_as_declared_output"], [])
            self.assertEqual(len(explanation["observed_worktree_changes"]), 1)
            self.assertFalse(explanation["causal_attribution_implied"])
            observation = explanation["observed_worktree_changes"][0]["observation"]
            self.assertEqual(observation["change_kind"], "added")
            self.assertFalse(observation["causal_attribution_implied"])

    def test_replay_reuses_first_execution_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = TestamurReceiptStore(root / "testamur.sqlite3")
            original = self.make_receipt(root)
            first = store.record(original)

            replay = dict(original)
            replay["replayed"] = True
            replay["input_artifacts"] = [
                {
                    "role": "input",
                    "declared_path": "input.txt",
                    "resolved_path": str(root / "input.txt"),
                    "status": "not_attributed_replay",
                    "snapshot": None,
                }
            ]
            second = store.record(replay)
            self.assertTrue(second["replayed_receipt_reused"])
            self.assertEqual(second["receipt_digest"], first["receipt_digest"])
            persisted = store.get(original["run_id"])
            assert persisted is not None
            self.assertFalse(persisted["replayed"])
            self.assertEqual(
                persisted["input_artifacts"][0]["status"],
                "captured",
            )

    def test_non_replay_cannot_rebind_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = TestamurReceiptStore(root / "testamur.sqlite3")
            original = self.make_receipt(root)
            store.record(original)
            conflicting = dict(original)
            conflicting["argv"] = ["python", "different.py"]
            with self.assertRaises(ValueError):
                store.record(conflicting)


if __name__ == "__main__":
    unittest.main()
