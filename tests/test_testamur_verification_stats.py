from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.receipt_store import TestamurReceiptStore
from testamur.verification_store import TestamurVerificationStore


class TestamurVerificationStatsTest(unittest.TestCase):
    def _checker(self, run_id: str, exit_code: int) -> dict:
        return {
            "run_id": run_id,
            "state": "finished",
            "argv": ["checker", run_id],
            "cwd": ".",
            "exit_code": exit_code,
            "record_digest": f"sha256:{run_id}",
            "verification_implied": False,
            "replayed": False,
            "git_context": {"before": {}, "after": {}},
            "worktree_delta": {"status": "disabled"},
            "input_artifacts": [],
            "output_artifacts": [],
        }

    def test_stats_count_current_target_state_not_each_historical_record(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("same revision\n", encoding="utf-8")
            receipts = TestamurReceiptStore(root / "testamur.sqlite3")
            store = TestamurVerificationStore(receipts)

            passed = self._checker("tst:run:stats-pass", 0)
            receipts.record(passed)
            store.record(
                "target.txt",
                root=root,
                verifier="checker-a",
                checker_receipt=passed,
            )

            failed = self._checker("tst:run:stats-fail", 1)
            receipts.record(failed)
            store.record(
                "target.txt",
                root=root,
                verifier="checker-b",
                checker_receipt=failed,
            )

            stats = store.stats(root=root)
            self.assertEqual(stats["records"], 2)
            self.assertEqual(stats["targets"], 1)
            self.assertEqual(stats["state_unit"], "targets")
            self.assertEqual(stats["current_passes"], 0)
            self.assertEqual(stats["current_failures"], 1)
            self.assertEqual(stats["target_states"]["current_checker_failure"], 1)
            self.assertEqual(
                stats["historical_record_states"]["current_pass_records"],
                1,
            )
            self.assertEqual(
                stats["historical_record_states"]["current_failure_records"],
                1,
            )

    def test_stale_and_not_assessable_are_target_states(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("v1\n", encoding="utf-8")
            receipts = TestamurReceiptStore(root / "testamur.sqlite3")
            store = TestamurVerificationStore(receipts)

            artifact_checker = self._checker("tst:run:artifact-checker", 0)
            receipts.record(artifact_checker)
            store.record(
                "target.txt",
                root=root,
                verifier="artifact-checker",
                checker_receipt=artifact_checker,
            )

            logical_checker = self._checker("tst:run:logical-checker-stats", 0)
            receipts.record(logical_checker)
            store.record(
                "claim:alpha",
                root=root,
                verifier="logical-checker",
                checker_receipt=logical_checker,
            )

            target.write_text("v2\n", encoding="utf-8")
            stats = store.stats(root=root)
            self.assertEqual(stats["targets"], 2)
            self.assertEqual(stats["stale_records"], 1)
            self.assertEqual(stats["not_assessable"], 1)
            self.assertEqual(stats["target_states"]["stale"], 1)
            self.assertEqual(stats["target_states"]["not_assessable"], 1)
            self.assertEqual(
                stats["historical_record_states"]["stale_records"],
                1,
            )
            self.assertEqual(
                stats["historical_record_states"]["not_assessable_records"],
                1,
            )


if __name__ == "__main__":
    unittest.main()
