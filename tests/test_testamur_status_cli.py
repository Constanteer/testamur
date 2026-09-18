from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from testamur.artifacts import snapshot_path
from testamur.entrypoint import main
from testamur.environment import initialize
from testamur.receipt_store import TestamurReceiptStore


class TestamurStatusCliTest(unittest.TestCase):
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

    def test_status_human_surface_shows_direct_transitive_and_total(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            env = initialize(root, name="status-cli")
            source = root / "source.txt"
            mid = root / "mid.txt"
            final = root / "final.txt"
            source.write_text("source-v1\n", encoding="utf-8")
            mid.write_text("mid-v1\n", encoding="utf-8")
            final.write_text("final-v1\n", encoding="utf-8")
            store = TestamurReceiptStore(env.database_path)
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:status-cli-producer",
                    input_name="source.txt",
                    output_name="mid.txt",
                )
            )
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:status-cli-consumer",
                    input_name="mid.txt",
                    output_name="final.txt",
                )
            )
            source.write_text("source-v2\n", encoding="utf-8")

            previous = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(["status"])
                rendered = output.getvalue()
                self.assertEqual(code, 0, rendered)
                self.assertIn("Revalidation · dependency propagation", rendered)
                self.assertIn("direct runs           1", rendered)
                self.assertIn("transitive runs       1", rendered)
                self.assertIn("total runs            2", rendered)
                self.assertIn("complete within budget", rendered)
                self.assertIn("1 direct + 1 transitive", rendered)
                self.assertIn("does not prove downstream conclusions false", rendered)
            finally:
                os.chdir(previous)

    def test_recursive_trace_human_surface_reports_revision_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            env = initialize(root, name="trace-mismatch-cli")
            source = root / "source.txt"
            mid = root / "mid.txt"
            final = root / "final.txt"
            source.write_text("source-v1\n", encoding="utf-8")
            mid.write_text("mid-v1\n", encoding="utf-8")
            final.write_text("final-v1\n", encoding="utf-8")
            store = TestamurReceiptStore(env.database_path)
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:old-producer-cli",
                    input_name="source.txt",
                    output_name="mid.txt",
                )
            )
            mid.write_text("mid-v2\n", encoding="utf-8")
            final.write_text("final-v2\n", encoding="utf-8")
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:new-consumer-cli",
                    input_name="mid.txt",
                    output_name="final.txt",
                )
            )

            previous = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(["trace", "final.txt", "--recursive"])
                rendered = output.getvalue()
                self.assertEqual(code, 0, rendered)
                self.assertIn("historical producer revisions skipped", rendered)
                self.assertIn("tst:run:old-producer-cli", rendered)
                self.assertIn("different_revision", rendered)
                self.assertIn("1 revision mismatches", rendered)
            finally:
                os.chdir(previous)

    def test_recursive_impact_human_surface_reports_revision_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            env = initialize(root, name="impact-mismatch-cli")
            source = root / "source.txt"
            mid = root / "mid.txt"
            final = root / "final.txt"
            source.write_text("source-v1\n", encoding="utf-8")
            mid.write_text("mid-v1\n", encoding="utf-8")
            final.write_text("final-v1\n", encoding="utf-8")
            store = TestamurReceiptStore(env.database_path)
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:old-producer-impact-cli",
                    input_name="source.txt",
                    output_name="mid.txt",
                )
            )
            mid.write_text("mid-v2\n", encoding="utf-8")
            final.write_text("final-v2\n", encoding="utf-8")
            store.record(
                self._receipt(
                    root=root,
                    run_id="tst:run:new-consumer-impact-cli",
                    input_name="mid.txt",
                    output_name="final.txt",
                )
            )
            source.write_text("source-v2\n", encoding="utf-8")

            previous = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(["impact", "source.txt", "--recursive"])
                rendered = output.getvalue()
                self.assertEqual(code, 0, rendered)
                self.assertIn("historical revision edges skipped", rendered)
                self.assertIn("tst:run:new-consumer-impact-cli", rendered)
                self.assertIn("different_revision", rendered)
                self.assertIn("1 revision mismatches", rendered)
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
