from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.artifacts import snapshot_path


class TestamurArtifactsNamespaceTest(unittest.TestCase):
    def test_snapshot_function_is_owned_by_testamur(self) -> None:
        self.assertEqual(snapshot_path.__module__, "testamur.artifacts")

    def test_file_snapshot_serialization_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / "fixture.txt"
            path.write_bytes(b"testamur\n")
            snapshot = snapshot_path(path, root=root)
            self.assertEqual(snapshot["artifact_type"], "file")
            self.assertEqual(snapshot["logical_path"], "fixture.txt")
            self.assertEqual(snapshot["byte_size"], 9)
            self.assertEqual(
                snapshot["content_hash"],
                "f573977bc82f7c0ecde28951dfdd6649efb1b7332f1c4bd3d56bc54a74704f05",
            )

    def test_tree_snapshot_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            tree = root / "tree"
            tree.mkdir()
            (tree / "b.txt").write_text("b", encoding="utf-8")
            (tree / "a.txt").write_text("a", encoding="utf-8")
            first = snapshot_path(tree, root=root)
            second = snapshot_path(tree, root=root)
            self.assertEqual(first, second)
            self.assertEqual([item["path"] for item in first["manifest"]], ["a.txt", "b.txt"])


if __name__ == "__main__":
    unittest.main()
