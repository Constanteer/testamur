from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from testamur.artifacts import snapshot_path
from testamur.entrypoint import main
from testamur.environment import initialize
from testamur.receipt_store import TestamurReceiptStore


class TestamurGraphCliTest(unittest.TestCase):
    def _record_chain(self, root: Path, store: TestamurReceiptStore) -> None:
        source = root / "source.txt"
        mid = root / "mid.txt"
        final = root / "final.txt"
        source.write_text("source-v1\n", encoding="utf-8")
        mid.write_text("mid-v1\n", encoding="utf-8")
        final.write_text("final-v1\n", encoding="utf-8")

        def receipt(run_id: str, input_name: str, output_name: str) -> dict:
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

        store.record(receipt("tst:run:producer", "source.txt", "mid.txt"))
        store.record(receipt("tst:run:consumer", "mid.txt", "final.txt"))

    def test_recursive_impact_json_is_available_from_public_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            env = initialize(root, name="graph-cli")
            store = TestamurReceiptStore(env.database_path)
            self._record_chain(root, store)
            (root / "source.txt").write_text("source-v2\n", encoding="utf-8")

            previous = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(
                        [
                            "--json",
                            "impact",
                            "source.txt",
                            "--recursive",
                            "--max-depth",
                            "4",
                        ]
                    )
                value = json.loads(output.getvalue())
                self.assertEqual(code, 0, value)
                self.assertTrue(value["traversal"]["recursive"])
                self.assertEqual(value["traversal"]["max_depth"], 4)
                self.assertEqual(len(value["consumers"]), 1)
                self.assertEqual(len(value["transitive_consumers"]), 1)
                self.assertEqual(
                    value["transitive_consumers"][0]["run_id"],
                    "tst:run:consumer",
                )
            finally:
                os.chdir(previous)

    def test_recursive_trace_human_output_shows_hop_depth(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            env = initialize(root, name="graph-cli-trace")
            store = TestamurReceiptStore(env.database_path)
            self._record_chain(root, store)

            previous = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(["trace", "final.txt", "--recursive"])
                rendered = output.getvalue()
                self.assertEqual(code, 0, rendered)
                self.assertIn("transitive upstream observed runs", rendered)
                self.assertIn("↑2", rendered)
                self.assertIn("tst:run:producer", rendered)
                self.assertIn("max depth 8", rendered)
            finally:
                os.chdir(previous)

    def test_depth_limit_is_reported_as_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            env = initialize(root, name="graph-cli-depth")
            store = TestamurReceiptStore(env.database_path)
            self._record_chain(root, store)
            (root / "source.txt").write_text("source-v2\n", encoding="utf-8")

            previous = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(
                        ["impact", "source.txt", "--recursive", "--max-depth", "1"]
                    )
                rendered = output.getvalue()
                self.assertEqual(code, 0, rendered)
                self.assertIn("truncated at requested max depth", rendered)
            finally:
                os.chdir(previous)

    def test_show_observation_id(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            env = initialize(root, name="graph-cli-show-observation")
            store = TestamurReceiptStore(env.database_path)
            self._record_chain(root, store)
            observation = store.observations_for_path("mid.txt", root=root)[0]

            previous = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(["show", observation["observation_id"]])
                rendered = output.getvalue()
                self.assertEqual(code, 0, rendered)
                self.assertIn("Testamur show — observation", rendered)
                self.assertIn(observation["observation_id"], rendered)
                self.assertIn(observation["run_id"], rendered)
            finally:
                os.chdir(previous)

    def test_graph_help_exposes_recursive_controls(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["impact", "--help"])
        self.assertEqual(code, 0)
        rendered = output.getvalue()
        self.assertIn("--recursive", rendered)
        self.assertIn("--max-depth", rendered)


if __name__ == "__main__":
    unittest.main()
