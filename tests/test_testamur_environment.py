from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from testamur.artifacts import snapshot_path
from testamur.cli import _prepare_argv
from testamur.environment import discover, initialize


class TestamurEnvironmentTest(unittest.TestCase):
    def test_initialize_and_discover_from_nested_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            env = initialize(root, name="demo")
            found = discover(nested)
            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual(found.root, root.resolve())
            self.assertEqual(found.config["name"], "demo")
            self.assertEqual(found.database_path, env.database_path)

    def test_initialize_inside_existing_environment_reuses_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            first = initialize(root, name="demo")
            second = initialize(nested, name="must-not-create-nested")
            self.assertEqual(second.root, first.root)
            self.assertEqual(second.config_path, first.config_path)
            self.assertFalse((nested / ".testamur").exists())

    def test_initialize_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            first = initialize(root, name="demo")
            second = initialize(root, name="ignored-on-second-init")
            self.assertEqual(first.config_path, second.config_path)
            self.assertEqual(second.config["name"], "demo")

    def test_git_environment_is_locally_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            initialize(root, name="demo")
            status = subprocess.run(
                ["git", "status", "--porcelain=v1", "--untracked-files=normal"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(status, "")

    def test_environment_directory_is_not_part_of_project_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "source.txt").write_text("hello\n", encoding="utf-8")
            initialize(root, name="demo")
            snapshot = snapshot_path(root, root=root.parent)
            manifest = snapshot.get("manifest") or []
            paths = {str(item.get("path")) for item in manifest}
            self.assertIn("source.txt", paths)
            self.assertFalse(any(path.startswith(".testamur/") for path in paths))

    def test_double_dash_is_shorthand_for_run(self) -> None:
        self.assertEqual(
            _prepare_argv(["--", "pytest", "-q"]),
            ["run", "--", "pytest", "-q"],
        )

    def test_json_double_dash_preserves_machine_mode(self) -> None:
        self.assertEqual(
            _prepare_argv(["--json", "--", "pytest", "-q"]),
            ["--json", "run", "--", "pytest", "-q"],
        )


if __name__ == "__main__":
    unittest.main()
