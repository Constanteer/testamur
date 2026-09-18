from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from testamur import __version__
from testamur.artifacts import snapshot_path
from testamur.entrypoint import main, normalize_argv
from testamur.environment import initialize
from testamur.receipt_store import TestamurReceiptStore
from testamur.verification_store import TestamurVerificationStore


class TestamurEntrypointTest(unittest.TestCase):
    def test_json_is_hoisted_before_subcommand(self) -> None:
        self.assertEqual(
            normalize_argv(["status", "--json"]),
            ["--json", "status"],
        )
        self.assertEqual(
            normalize_argv(["why", "artifact.txt", "--json"]),
            ["--json", "why", "artifact.txt"],
        )

    def test_json_after_separator_is_preserved_for_wrapped_command(self) -> None:
        self.assertEqual(
            normalize_argv(["run", "--", "tool", "--json"]),
            ["run", "--", "tool", "--json"],
        )
        self.assertEqual(
            normalize_argv(["--json", "run", "--", "tool", "--json"]),
            ["--json", "run", "--", "tool", "--json"],
        )

    def test_version_does_not_enter_cli_parser(self) -> None:
        output = io.StringIO()
        with patch("testamur.entrypoint.cli_main") as cli_main:
            with contextlib.redirect_stdout(output):
                code = main(["--version"])
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue().strip(), f"testamur {__version__}")
        cli_main.assert_not_called()

    def test_machine_version_is_json(self) -> None:
        output = io.StringIO()
        with patch("testamur.entrypoint.cli_main") as cli_main:
            with contextlib.redirect_stdout(output):
                code = main(["--json", "--version"])
        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads(output.getvalue()),
            {"ok": True, "testamur_version": __version__},
        )
        cli_main.assert_not_called()

    def test_bare_invocation_renders_public_help(self) -> None:
        output = io.StringIO()
        with patch("testamur.entrypoint.cli_main") as cli_main:
            with contextlib.redirect_stdout(output):
                code = main([])
        rendered = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("usage: testamur", rendered)
        self.assertIn("show <target>", rendered)
        self.assertIn("--recursive", rendered)
        self.assertIn("tst:run:*", rendered)
        self.assertIn("tst:obs:*", rendered)
        self.assertNotIn("wtn:run:*", rendered)
        cli_main.assert_not_called()

    def test_machine_missing_command_has_stable_error(self) -> None:
        output = io.StringIO()
        with patch("testamur.entrypoint.cli_main") as cli_main:
            with contextlib.redirect_stdout(output):
                code = main(["--json"])
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(output.getvalue())["error"]["code"],
            "missing_command",
        )
        cli_main.assert_not_called()

    def test_empty_run_is_rejected_before_runtime(self) -> None:
        error = io.StringIO()
        with patch("testamur.entrypoint.cli_main") as cli_main:
            with contextlib.redirect_stderr(error):
                code = main(["run"])
        self.assertEqual(code, 2)
        self.assertIn("no command", error.getvalue())
        cli_main.assert_not_called()

    def test_show_artifact_uses_local_durable_observation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            env = initialize(root, name="entrypoint-show")
            target = root / "result.txt"
            target.write_text("result\n", encoding="utf-8")
            receipt = {
                "run_id": "tst:run:entrypoint-show",
                "state": "finished",
                "argv": ["tool"],
                "cwd": str(root),
                "exit_code": 0,
                "record_digest": "sha256:entrypoint-show",
                "verification_implied": False,
                "replayed": False,
                "git_context": {"before": {}, "after": {}},
                "worktree_delta": {"status": "disabled"},
                "input_artifacts": [],
                "output_artifacts": [
                    {
                        "role": "output",
                        "declared_path": "result.txt",
                        "resolved_path": str(target),
                        "status": "captured",
                        "snapshot": snapshot_path(target, root=root),
                    }
                ],
            }
            TestamurReceiptStore(env.database_path).record(receipt)

            previous = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with patch("testamur.entrypoint.cli_main") as cli_main:
                    with contextlib.redirect_stdout(output):
                        code = main(["show", "result.txt"])
                self.assertEqual(code, 0, output.getvalue())
                self.assertIn("Testamur show", output.getvalue())
                self.assertIn("artifact", output.getvalue())
                self.assertIn("observed as declared output", output.getvalue())
                cli_main.assert_not_called()
            finally:
                os.chdir(previous)

    def test_show_verification_id_reports_current_revision_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            env = initialize(root, name="entrypoint-verification")
            target = root / "target.txt"
            target.write_text("target\n", encoding="utf-8")
            receipts = TestamurReceiptStore(env.database_path)
            checker = {
                "run_id": "tst:run:entrypoint-checker",
                "state": "finished",
                "argv": ["checker"],
                "cwd": str(root),
                "exit_code": 0,
                "record_digest": "sha256:entrypoint-checker",
                "verification_implied": False,
                "replayed": False,
                "git_context": {"before": {}, "after": {}},
                "worktree_delta": {"status": "disabled"},
                "input_artifacts": [],
                "output_artifacts": [],
            }
            receipts.record(checker)
            verifications = TestamurVerificationStore(receipts)
            record = verifications.record(
                "target.txt",
                root=root,
                verifier="checker",
                checker_receipt=checker,
            )

            previous = Path.cwd()
            try:
                os.chdir(root)
                current_output = io.StringIO()
                with patch("testamur.entrypoint.cli_main") as cli_main:
                    with contextlib.redirect_stdout(current_output):
                        current_code = main(["show", record["verification_id"]])
                current_rendered = current_output.getvalue()
                self.assertEqual(current_code, 0, current_rendered)
                self.assertIn("Testamur show — verification", current_rendered)
                self.assertIn(record["verification_id"], current_rendered)
                self.assertIn("revision      current", current_rendered)
                cli_main.assert_not_called()

                target.write_text("changed\n", encoding="utf-8")
                stale_output = io.StringIO()
                with contextlib.redirect_stdout(stale_output):
                    stale_code = main(["--json", "show", record["verification_id"]])
                stale_value = json.loads(stale_output.getvalue())
                self.assertEqual(stale_code, 0, stale_value)
                self.assertEqual(stale_value["kind"], "verification")
                self.assertEqual(stale_value["revision_state"], "stale")
                self.assertEqual(stale_value["target_verification_state"], "stale")
            finally:
                os.chdir(previous)

    def test_normalized_arguments_reach_cli(self) -> None:
        with patch("testamur.entrypoint.cli_main", return_value=0) as cli_main:
            code = main(["status", "--json"])
        self.assertEqual(code, 0)
        cli_main.assert_called_once_with(["--json", "status"])

    def test_argparse_system_exit_becomes_return_code(self) -> None:
        with patch("testamur.entrypoint.cli_main", side_effect=SystemExit(2)):
            self.assertEqual(main(["nope"]), 2)


if __name__ == "__main__":
    unittest.main()
