from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.artifacts import snapshot_path
from testamur.receipt_store import TestamurReceiptStore


class TestamurRevisionGraphTest(unittest.TestCase):
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

    def test_recursive_trace_does_not_cross_different_artifact_revision(self) -> None:
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
                    run_id="tst:run:old-producer",
                    input_name="source.txt",
                    output_name="mid.txt",
                )
            )

            # A later run consumes a different revision of the same path.
            mid.write_text("mid-v2\n", encoding="utf-8")
            final.write_text("final-v2\n", encoding="utf-8")
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:new-consumer",
                    input_name="mid.txt",
                    output_name="final.txt",
                )
            )

            value = store.trace("final.txt", root=root, recursive=True)
            self.assertEqual(
                [item["run_id"] for item in value["upstream_observed_runs"]],
                ["tst:run:new-consumer"],
            )
            self.assertEqual(value["transitive_upstream_runs"], [])
            self.assertEqual(len(value["revision_mismatched_producers"]), 1)
            mismatch = value["revision_mismatched_producers"][0]
            self.assertEqual(mismatch["run_id"], "tst:run:old-producer")
            self.assertEqual(mismatch["revision_relation"], "different_revision")
            self.assertEqual(value["traversal"]["revision_mismatches"], 1)
            self.assertTrue(value["semantics"]["revision_aware_traversal"])
            self.assertTrue(value["semantics"]["different_revisions_are_not_traversed"])

    def test_recursive_impact_does_not_revalidate_consumer_of_other_revision(self) -> None:
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
                    run_id="tst:run:old-producer",
                    input_name="source.txt",
                    output_name="mid.txt",
                )
            )

            mid.write_text("mid-v2\n", encoding="utf-8")
            final.write_text("final-v2\n", encoding="utf-8")
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:new-consumer",
                    input_name="mid.txt",
                    output_name="final.txt",
                )
            )

            source.write_text("source-v2\n", encoding="utf-8")
            value = store.impact("source.txt", root=root, recursive=True)
            self.assertEqual(
                [item["run_id"] for item in value["consumers"]],
                ["tst:run:old-producer"],
            )
            self.assertEqual(value["transitive_consumers"], [])
            self.assertEqual(
                [item["path"] for item in value["potentially_affected_observations"]],
                ["mid.txt"],
            )
            self.assertEqual(len(value["revision_mismatched_edges"]), 1)
            mismatch = value["revision_mismatched_edges"][0]
            self.assertEqual(mismatch["consumer_run_id"], "tst:run:new-consumer")
            self.assertEqual(mismatch["revision_relation"], "different_revision")
            self.assertEqual(value["traversal"]["revision_mismatches"], 1)
            self.assertTrue(value["semantics"]["different_revisions_are_not_traversed"])

    def test_missing_revision_hash_is_conservative_not_equal(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.txt"
            mid = root / "mid.txt"
            final = root / "final.txt"
            source.write_text("source-v1\n", encoding="utf-8")
            mid.write_text("mid-v1\n", encoding="utf-8")
            final.write_text("final-v1\n", encoding="utf-8")
            store = TestamurReceiptStore(root / "testamur.sqlite3")

            producer = self._receipt(
                root=root,
                run_id="tst:run:producer-unknown-link",
                input_name="source.txt",
                output_name="mid.txt",
            )
            store.record(producer)

            consumer = self._receipt(
                root=root,
                run_id="tst:run:consumer-unknown-link",
                input_name="mid.txt",
                output_name="final.txt",
            )
            consumer["input_artifacts"][0]["snapshot"] = None
            consumer["input_artifacts"][0]["status"] = "capture_failed"
            store.record(consumer)

            source.write_text("source-v2\n", encoding="utf-8")
            value = store.impact("source.txt", root=root, recursive=True)
            self.assertEqual(len(value["transitive_consumers"]), 1)
            self.assertEqual(
                value["transitive_consumers"][0]["revision_relation"],
                "not_assessable",
            )
            self.assertTrue(value["semantics"]["missing_revision_hash_is_not_assessable"])


if __name__ == "__main__":
    unittest.main()
