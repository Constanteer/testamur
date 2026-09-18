from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.artifacts import snapshot_path
from testamur.receipt_store import TestamurReceiptStore


class TestamurEvidenceGraphTest(unittest.TestCase):
    def _receipt(
        self,
        *,
        root: Path,
        run_id: str,
        input_path: str,
        output_path: str,
    ) -> dict:
        source = root / input_path
        output = root / output_path
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
                    "declared_path": input_path,
                    "resolved_path": str(source),
                    "status": "captured",
                    "snapshot": snapshot_path(source, root=root),
                }
            ],
            "output_artifacts": [
                {
                    "role": "output",
                    "declared_path": output_path,
                    "resolved_path": str(output),
                    "status": "captured",
                    "snapshot": snapshot_path(output, root=root),
                }
            ],
        }

    def _chain(self, root: Path) -> TestamurReceiptStore:
        source = root / "source.txt"
        mid = root / "mid.txt"
        final = root / "final.txt"
        source.write_text("source-v1\n", encoding="utf-8")
        mid.write_text("mid-v1\n", encoding="utf-8")
        final.write_text("final-v1\n", encoding="utf-8")

        store = TestamurReceiptStore(root / "testamur.sqlite3")
        store.record(self._receipt(root=root, run_id="tst:run:producer", input_path="source.txt", output_path="mid.txt"))
        store.record(self._receipt(root=root, run_id="tst:run:consumer", input_path="mid.txt", output_path="final.txt"))
        return store

    def test_recursive_impact_propagates_revalidation_not_falsehood(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = self._chain(root)
            (root / "source.txt").write_text("source-v2\n", encoding="utf-8")
            shallow = store.impact("source.txt", root=root)
            self.assertEqual(len(shallow["consumers"]), 1)
            self.assertEqual(shallow["consumers"][0]["run_id"], "tst:run:producer")
            self.assertEqual(shallow["transitive_consumers"], [])
            self.assertEqual([item["path"] for item in shallow["potentially_affected_observations"]], ["mid.txt"])
            self.assertFalse(shallow["semantics"]["recursive_impact"])

            recursive = store.impact("source.txt", root=root, recursive=True)
            self.assertEqual(len(recursive["consumers"]), 1)
            self.assertEqual(len(recursive["transitive_consumers"]), 1)
            downstream = recursive["transitive_consumers"][0]
            self.assertEqual(downstream["run_id"], "tst:run:consumer")
            self.assertEqual(downstream["depth"], 2)
            self.assertEqual(downstream["state"], "requires_revalidation_due_to_upstream")
            self.assertEqual({item["path"] for item in recursive["potentially_affected_observations"]}, {"mid.txt", "final.txt"})
            self.assertTrue(recursive["semantics"]["recursive_impact"])
            self.assertTrue(recursive["semantics"]["upstream_uncertainty_propagates_revalidation"])
            self.assertFalse(recursive["semantics"]["change_implies_invalidation"])
            self.assertFalse(recursive["semantics"]["causal_attribution_implied"])
            self.assertFalse(recursive["traversal"]["truncated"])

    def test_recursive_impact_honors_depth_limit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = self._chain(root)
            (root / "source.txt").write_text("source-v2\n", encoding="utf-8")
            value = store.impact("source.txt", root=root, recursive=True, max_depth=1)
            self.assertEqual(value["transitive_consumers"], [])
            self.assertEqual([item["path"] for item in value["potentially_affected_observations"]], ["mid.txt"])
            self.assertTrue(value["traversal"]["truncated"])
            self.assertEqual(value["traversal"]["max_depth"], 1)

    def test_recursive_trace_walks_persisted_producer_chain(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = self._chain(root)
            shallow = store.trace("final.txt", root=root)
            self.assertEqual([item["run_id"] for item in shallow["upstream_observed_runs"]], ["tst:run:consumer"])
            self.assertEqual(shallow["transitive_upstream_runs"], [])
            recursive = store.trace("final.txt", root=root, recursive=True)
            self.assertEqual([item["run_id"] for item in recursive["upstream_observed_runs"]], ["tst:run:consumer"])
            self.assertEqual([item["run_id"] for item in recursive["transitive_upstream_runs"]], ["tst:run:producer"])
            self.assertEqual(recursive["transitive_upstream_runs"][0]["depth"], 2)
            self.assertEqual(recursive["transitive_upstream_runs"][0]["via_artifact"], "mid.txt")
            self.assertTrue(recursive["semantics"]["recursive_trace"])
            self.assertTrue(recursive["semantics"]["trace_uses_persisted_observations"])
            self.assertFalse(recursive["semantics"]["causal_attribution_implied"])
            self.assertEqual(recursive["traversal"]["runs_observed"], 2)

    def test_run_target_trace_can_walk_its_declared_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = self._chain(root)
            value = store.trace("tst:run:consumer", root=root, recursive=True)
            self.assertEqual(value["kind"], "run")
            self.assertEqual([item["run_id"] for item in value["upstream_observed_runs"]], ["tst:run:producer"])
            self.assertEqual(value["upstream_observed_runs"][0]["via_artifact"], "mid.txt")

    def test_observation_identity_is_directly_retrievable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = self._chain(root)
            observations = store.observations_for_path("mid.txt", root=root)
            self.assertGreaterEqual(len(observations), 2)
            observation = observations[0]
            loaded = store.get_observation(observation["observation_id"])
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded["observation_id"], observation["observation_id"])
            self.assertEqual(loaded["run_id"], observation["run_id"])
            self.assertEqual(loaded["role"], observation["role"])

    def test_invalid_depth_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = self._chain(root)
            with self.assertRaises(ValueError):
                store.trace("final.txt", root=root, recursive=True, max_depth=0)
            with self.assertRaises(ValueError):
                store.impact("source.txt", root=root, recursive=True, max_depth=0)


if __name__ == "__main__":
    unittest.main()
