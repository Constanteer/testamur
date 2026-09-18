from __future__ import annotations

from pathlib import Path
import unittest

from testamur.namespace_gate import scan_python_namespace_dependencies


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "testamur"


class TestamurProductionNamespaceGateTest(unittest.TestCase):
    def test_canonical_package_has_no_static_or_literal_dynamic_retired_runtime_imports(self) -> None:
        violations = scan_python_namespace_dependencies(CANONICAL)
        self.assertEqual(
            violations,
            (),
            "release-blocking reverse namespace edges remain:\n"
            + "\n".join(item.render() for item in violations),
        )


if __name__ == "__main__":
    unittest.main()
