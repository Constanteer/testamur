from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.receipt_store import TestamurReceiptStore
from testamur.verification_store import TestamurVerificationStore


class TestamurVerificationStoreTest(unittest.TestCase):
    def checker_receipt(self, run_id: str, exit_code: int) -> dict:
        return {
            "run_id": run_id,
            "state": "finished",
            "argv": ["checker"],
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

    def test_passing_checker_is_revision_pinned_and_becomes_stale(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("v1\n", encoding="utf-8")
            receipts = TestamurReceiptStore(root / "testamur.sqlite3")
            checker = self.checker_receipt("tst:run:checker-pass", 0)
            receipts.record(checker)
            store = TestamurVerificationStore(receipts)
            record = store.record(
                "target.txt",
                root=root,
                verifier="pytest",
                checker_receipt=checker,
            )
            self.assertEqual(record["checker_status"], "passed")
            self.assertTrue(record["semantics"]["path_revision_pinned"])
            self.assertFalse(record["semantics"]["checker_pass_implies_universal_truth"])

            current = store.for_target("target.txt", root=root)
            self.assertEqual(current["verification_state"], "current_checker_pass")
            self.assertEqual(current["records"][0]["revision_state"], "current")

            target.write_text("v2\n", encoding="utf-8")
            stale = store.for_target("target.txt", root=root)
            self.assertEqual(stale["verification_state"], "stale")
            self.assertEqual(stale["stale_records"], 1)
            self.assertFalse(stale["semantics"]["checker_pass_implies_universal_truth"])

    def test_prepared_revision_survives_checker_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("before\n", encoding="utf-8")
            receipts = TestamurReceiptStore(root / "testamur.sqlite3")
            store = TestamurVerificationStore(receipts)
            prepared = store.prepare_target_revision("target.txt", root=root)

            # Simulate a checker that mutates the target before its receipt is bound.
            target.write_text("after\n", encoding="utf-8")
            checker = self.checker_receipt("tst:run:checker-mutated", 0)
            receipts.record(checker)
            record = store.record(
                "target.txt",
                root=root,
                verifier="mutating-checker",
                checker_receipt=checker,
                target_revision=prepared,
            )
            self.assertEqual(
                record["target_revision_status"],
                "captured_before_checker",
            )
            self.assertTrue(
                record["semantics"]["target_revision_captured_before_checker"]
            )
            state = store.for_target("target.txt", root=root)
            self.assertEqual(state["verification_state"], "stale")

    def test_checker_failure_does_not_assert_target_false(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("value\n", encoding="utf-8")
            receipts = TestamurReceiptStore(root / "testamur.sqlite3")
            checker = self.checker_receipt("tst:run:checker-fail", 1)
            receipts.record(checker)
            store = TestamurVerificationStore(receipts)
            record = store.record(
                "target.txt",
                root=root,
                verifier="lint",
                checker_receipt=checker,
            )
            self.assertEqual(record["checker_status"], "failed")
            self.assertFalse(record["semantics"]["checker_failure_implies_target_false"])
            state = store.for_target("target.txt", root=root)
            self.assertEqual(state["verification_state"], "current_checker_failure")
            self.assertFalse(state["semantics"]["checker_failure_implies_target_false"])

    def test_latest_current_checker_controls_current_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("same revision\n", encoding="utf-8")
            receipts = TestamurReceiptStore(root / "testamur.sqlite3")
            store = TestamurVerificationStore(receipts)

            passed = self.checker_receipt("tst:run:checker-pass-first", 0)
            receipts.record(passed)
            store.record(
                "target.txt",
                root=root,
                verifier="checker-a",
                checker_receipt=passed,
            )

            failed = self.checker_receipt("tst:run:checker-fail-latest", 2)
            receipts.record(failed)
            store.record(
                "target.txt",
                root=root,
                verifier="checker-b",
                checker_receipt=failed,
            )

            state = store.for_target("target.txt", root=root)
            self.assertEqual(state["current_passes"], 1)
            self.assertEqual(state["current_failures"], 1)
            self.assertEqual(state["verification_state"], "current_checker_failure")
            self.assertEqual(
                state["latest_current_record"]["checker_run_id"],
                "tst:run:checker-fail-latest",
            )
            self.assertTrue(
                state["semantics"]["current_state_uses_latest_current_checker"]
            )

    def test_logical_target_is_explicitly_not_assessable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            receipts = TestamurReceiptStore(root / "testamur.sqlite3")
            checker = self.checker_receipt("tst:run:checker-logical", 0)
            receipts.record(checker)
            store = TestamurVerificationStore(receipts)
            record = store.record(
                "claim:alpha",
                root=root,
                verifier="logical-checker",
                checker_receipt=checker,
            )
            self.assertEqual(record["target_kind"], "logical_ref")

            state = store.for_target("claim:alpha", root=root)
            self.assertEqual(state["verification_state"], "not_assessable")
            self.assertEqual(state["not_assessable_records"], 1)
            self.assertIsNone(state["latest_current_record"])


if __name__ == "__main__":
    unittest.main()
