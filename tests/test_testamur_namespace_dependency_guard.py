from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTAMUR = ROOT / "testamur"


class TestamurNamespaceDependencyGuardTest(unittest.TestCase):
    def test_testamur_never_imports_retired_runtime(self) -> None:
        violations: list[str] = []
        for path in sorted(TESTAMUR.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in {"witness", "witness_service"} or alias.name.startswith(("witness.", "witness_service.")):
                            violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module in {"witness", "witness_service"} or module.startswith(("witness.", "witness_service.")):
                        violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: from {module}")
        self.assertEqual(
            violations,
            [],
            "Testamur must be the convergence target; reverse imports recreate the parallel substrate:\n"
            + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
