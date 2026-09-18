from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.artifacts import snapshot_path
from testamur.environment_status import revalidation_status
from testamur.receipt_store import TestamurReceiptStore


class TestamurEnvironmentStatusTest(unittest.TestCase):
    def test_changed_input_requires_revalidation_without_asserting_falsehood(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.txt"
            source.write_text("v1\n", encoding="utf-8")
            store = TestamurReceiptStore(root / "testamur.sqlite3")
            store.record(
                {
                    "run_id": "tst:run:status-test",
                    "state": "finished",
                    "argv": ["tool", "source.txt"],
                    "cwd": str(root),
                    "exit_code": 0,
                    "record_digest": "sha256:run",
                    "verification_implied": False,
                    "replayed": False,
                    "git_context": {"before": {}, "after": {}},
                    "worktree_delta": {"status": "disabled"},
                    "input_artifacts": [
                        {
                            "role": "input",
                            "declared_path": "source.txt",
                            "resolved_path": str(source),
                            "status": "captured",
                            "snapshot": snapshot_path(source, root=root),
                        }
                    ],
                    "output_artifacts": [],
                }
            )

            current = revalidation_status(store, root=root)
            self.assertEqual(current["paths_current"], 1)
            self.assertEqual(current["paths_requiring_revalidation"], 0)

            source.write_text("v2\n", encoding="utf-8")
            changed = revalidation_status(store, root=root)
            self.assertEqual(changed["paths_current"], 0)
            self.assertEqual(changed["paths_requiring_revalidation"], 1)
            self.assertEqual(changed["runs_requiring_revalidation"], 1)
            self.assertEqual(changed["details"][0]["state"], "requires_revalidation")
            self.assertFalse(changed["semantics"]["hash_mismatch_implies_false"])
            self.assertIsNone(changed["semantics"]["universal_trust_score"])

    def test_uncaptured_input_is_not_assessable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.txt"
            source.write_text("value\n", encoding="utf-8")
            store = TestamurReceiptStore(root / "testamur.sqlite3")
            store.record(
                {
                    "run_id": "tst:run:unknown-input",
                    "state": "finished",
                    "argv": ["tool"],
                    "cwd": str(root),
                    "exit_code": 0,
                    "record_digest": "sha256:unknown",
                    "verification_implied": False,
                    "replayed": False,
                    "git_context": {"before": {}, "after": {}},
                    "worktree_delta": {"status": "disabled"},
                    "input_artifacts": [
                        {
                            "role": "input",
                            "declared_path": "source.txt",
                            "resolved_path": str(source),
                            "status": "capture_failed",
                            "snapshot": None,
                        }
                    ],
                    "output_artifacts": [],
                }
            )
            result = revalidation_status(store, root=root)
            self.assertEqual(result["paths_not_assessable"], 1)
            self.assertEqual(result["paths_requiring_revalidation"], 0)


if __name__ == "__main__":
    unittest.main()
