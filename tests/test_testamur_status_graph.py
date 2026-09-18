from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.artifacts import snapshot_path
from testamur.environment_status import revalidation_status
from testamur.receipt_store import TestamurReceiptStore


class TestamurStatusGraphTest(unittest.TestCase):
    def _receipt(
        self,
        *,
        root: Path,
        run_id: str,
        input_name: str,
        output_name: str,
    ) -> dict:
        input_path = root / input_name
        output_path = root / output_name
        return {
            "run_id": run_id,
            "state": "finished",
            "argv": ["worker", run_id],
            "cwd": str(root),
            "exit_code": 0,
            "record_digest": f"sha256:{run_id}",
            "verification_implied": False,
            "replayed": False,
            "git_context": {"before": {}, "after": {}},
            "worktree_delta": {"status": "disabled"},
            "input_artifacts": [
                {
                    "role": "input",
                    "declared_path": input_name,
                    "resolved_path": str(input_path),
                    "status": "captured",
                    "snapshot": snapshot_path(input_path, root=root),
                }
            ],
            "output_artifacts": [
                {
                    "role": "output",
                    "declared_path": output_name,
                    "resolved_path": str(output_path),
                    "status": "captured",
                    "snapshot": snapshot_path(output_path, root=root),
                }
            ],
        }

    def test_status_propagates_revalidation_to_transitive_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.txt"
            mid = root / "mid.txt"
            final = root / "final.txt"
            source.write_text("source-v1\n", encoding="utf-8")
            mid.write_text("mid-v1\n", encoding="utf-8")
            final.write_text("final-v1\n", encoding="utf-8")

            store = TestamurReceiptStore(root / "testamur.sqlite3")
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:status-producer",
                    input_name="source.txt",
                    output_name="mid.txt",
                )
            )
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:status-consumer",
                    input_name="mid.txt",
                    output_name="final.txt",
                )
            )

            source.write_text("source-v2\n", encoding="utf-8")
            value = revalidation_status(store, root=root)
            self.assertEqual(value["direct_runs_requiring_revalidation"], 1)
            self.assertEqual(value["transitive_runs_requiring_revalidation"], 1)
            self.assertEqual(value["total_runs_requiring_revalidation"], 2)
            self.assertEqual(value["affected_observations_requiring_revalidation"], 2)
            self.assertEqual(value["affected_paths_requiring_revalidation"], 2)
            self.assertTrue(value["dependency_graph"]["revision_aware"])
            self.assertFalse(value["dependency_graph"]["truncated"])
            self.assertFalse(value["semantics"]["hash_mismatch_implies_false"])
            self.assertFalse(value["semantics"]["transitive_revalidation_implies_false"])

    def test_status_does_not_cross_known_revision_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.txt"
            mid = root / "mid.txt"
            final = root / "final.txt"
            source.write_text("source-v1\n", encoding="utf-8")
            mid.write_text("mid-v1\n", encoding="utf-8")
            final.write_text("final-v1\n", encoding="utf-8")

            store = TestamurReceiptStore(root / "testamur.sqlite3")
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:old-producer-status",
                    input_name="source.txt",
                    output_name="mid.txt",
                )
            )

            mid.write_text("mid-v2\n", encoding="utf-8")
            final.write_text("final-v2\n", encoding="utf-8")
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:new-consumer-status",
                    input_name="mid.txt",
                    output_name="final.txt",
                )
            )

            source.write_text("source-v2\n", encoding="utf-8")
            value = revalidation_status(store, root=root)
            # source.txt changed, so only the old producer is directly stale.
            # The newer consumer still sees the same mid.txt@v2 revision and
            # must not become transitively stale through the producer's v1 edge.
            self.assertEqual(value["direct_runs_requiring_revalidation"], 1)
            self.assertEqual(value["transitive_runs_requiring_revalidation"], 0)
            self.assertEqual(value["total_runs_requiring_revalidation"], 1)
            self.assertTrue(value["dependency_graph"]["revision_aware"])

    def test_graph_path_budget_reports_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            a = root / "a.txt"
            b = root / "b.txt"
            out_a = root / "out-a.txt"
            out_b = root / "out-b.txt"
            for path, value in (
                (a, "a-v1\n"),
                (b, "b-v1\n"),
                (out_a, "oa\n"),
                (out_b, "ob\n"),
            ):
                path.write_text(value, encoding="utf-8")
            store = TestamurReceiptStore(root / "testamur.sqlite3")
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:a",
                    input_name="a.txt",
                    output_name="out-a.txt",
                )
            )
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:b",
                    input_name="b.txt",
                    output_name="out-b.txt",
                )
            )
            a.write_text("a-v2\n", encoding="utf-8")
            b.write_text("b-v2\n", encoding="utf-8")

            value = revalidation_status(store, root=root, graph_path_limit=1)
            self.assertEqual(value["paths_requiring_revalidation"], 2)
            self.assertEqual(value["dependency_graph"]["paths_traversed"], 1)
            self.assertTrue(value["dependency_graph"]["truncated"])


if __name__ == "__main__":
    unittest.main()
