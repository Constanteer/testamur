from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

from testamur.cli import main
from testamur.environment import initialize
from testamur.receipt_store import TestamurReceiptStore
from testamur.verification_store import TestamurVerificationStore


class TestamurCliE2ETest(unittest.TestCase):
    def test_run_persists_receipt_and_declared_artifact_query(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            initialize(root, name="cli-e2e")
            previous = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(
                        [
                            "run",
                            "--output",
                            "result.txt",
                            "--",
                            sys.executable,
                            "-c",
                            "from pathlib import Path; Path('result.txt').write_text('ok\\n', encoding='utf-8')",
                        ]
                    )
                self.assertEqual(code, 0, output.getvalue())
                self.assertIn("tst:run:", output.getvalue())
                self.assertNotIn("wtn:run:", output.getvalue())
                self.assertTrue((root / "result.txt").exists())

                store = TestamurReceiptStore(root / ".testamur" / "testamur.sqlite3")
                self.assertEqual(store.stats()["runs"], 1)
                self.assertEqual(store.stats()["output_observations"], 1)
                explanation = store.explain("result.txt", root=root)
                self.assertEqual(explanation["kind"], "artifact")
                self.assertEqual(len(explanation["observed_as_declared_output"]), 1)
                self.assertFalse(explanation["causal_attribution_implied"])
                self.assertEqual(
                    explanation["verification"],
                    "not_inferred_from_artifact_observation",
                )

                why_output = io.StringIO()
                with contextlib.redirect_stdout(why_output):
                    why_code = main(["why", "result.txt"])
                self.assertEqual(why_code, 0, why_output.getvalue())
                self.assertIn("observed as declared output", why_output.getvalue())
                self.assertIn("verification", why_output.getvalue())
                self.assertIn("causality", why_output.getvalue())
            finally:
                os.chdir(previous)

    def test_worktree_delta_makes_changed_path_queryable_without_declaring_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            initialize(root, name="ambient-e2e")
            previous = Path.cwd()
            try:
                os.chdir(root)
                run_output = io.StringIO()
                with contextlib.redirect_stdout(run_output):
                    code = main(
                        [
                            "run",
                            "--worktree-delta",
                            "--",
                            sys.executable,
                            "-c",
                            "from pathlib import Path; Path('ambient.txt').write_text('observed\\n', encoding='utf-8')",
                        ]
                    )
                self.assertEqual(code, 0, run_output.getvalue())

                store = TestamurReceiptStore(root / ".testamur" / "testamur.sqlite3")
                self.assertEqual(store.stats()["worktree_change_observations"], 1)
                explanation = store.explain("ambient.txt", root=root)
                self.assertEqual(explanation["observed_as_declared_output"], [])
                self.assertEqual(len(explanation["observed_worktree_changes"]), 1)
                self.assertFalse(explanation["causal_attribution_implied"])

                why_output = io.StringIO()
                with contextlib.redirect_stdout(why_output):
                    why_code = main(["why", "ambient.txt"])
                rendered = why_output.getvalue()
                self.assertEqual(why_code, 0, rendered)
                self.assertIn("observed changed during run", rendered)
                self.assertIn("causal attribution: not implied", rendered)
            finally:
                os.chdir(previous)

    def test_verify_executes_checker_and_binds_pinned_target_revision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("checked\n", encoding="utf-8")
            initialize(root, name="verify-e2e")
            previous = Path.cwd()
            try:
                os.chdir(root)
                verify_output = io.StringIO()
                with contextlib.redirect_stdout(verify_output):
                    code = main(
                        [
                            "verify",
                            "target.txt",
                            "--with",
                            sys.executable,
                            "--",
                            "-c",
                            "import sys; sys.exit(0)",
                        ]
                    )
                rendered = verify_output.getvalue()
                self.assertEqual(code, 0, rendered)
                self.assertIn("checker finished", rendered)
                self.assertIn("current_checker_pass", rendered)

                receipts = TestamurReceiptStore(root / ".testamur" / "testamur.sqlite3")
                verifications = TestamurVerificationStore(receipts)
                state = verifications.for_target("target.txt", root=root)
                self.assertEqual(state["verification_state"], "current_checker_pass")
                self.assertEqual(state["current_passes"], 1)
                self.assertGreaterEqual(receipts.stats()["runs"], 1)

                why_output = io.StringIO()
                with contextlib.redirect_stdout(why_output):
                    why_code = main(["why", "target.txt"])
                why_rendered = why_output.getvalue()
                self.assertEqual(why_code, 0, why_rendered)
                self.assertIn("current_checker_pass", why_rendered)
                self.assertIn("universal truth", why_rendered)

                target.write_text("changed\n", encoding="utf-8")
                stale_output = io.StringIO()
                with contextlib.redirect_stdout(stale_output):
                    stale_code = main(["why", "target.txt"])
                self.assertEqual(stale_code, 0, stale_output.getvalue())
                self.assertIn("stale", stale_output.getvalue())
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
