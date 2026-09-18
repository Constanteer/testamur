from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.convergence import (
    LegacyModuleState,
    MigrationAction,
    forbidden_production_imports,
    legacy_import_report,
    legacy_namespace_readiness,
    scan_legacy_imports,
    scan_legacy_modules,
)


ROOT = Path(__file__).resolve().parents[1]


class TestamurConvergenceInventoryTest(unittest.TestCase):
    def test_scanner_classifies_static_and_literal_dynamic_imports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "testamur").mkdir()
            (root / "tests").mkdir()
            (root / "scripts").mkdir()
            (root / "app").mkdir()
            (root / "witness").mkdir()
            (root / "testamur" / "bad.py").write_text(
                "from witness.model import canonical_hash\n", encoding="utf-8"
            )
            (root / "tests" / "legacy.py").write_text(
                "import witness.reliance\n", encoding="utf-8"
            )
            (root / "scripts" / "dynamic.py").write_text(
                "import importlib\nimportlib.import_module('witness.runtime_protocol')\n",
                encoding="utf-8",
            )
            (root / "app" / "dynamic.py").write_text(
                "__import__('witness')\n", encoding="utf-8"
            )
            (root / "witness" / "old.py").write_text(
                "from witness.model import canonical_hash\n", encoding="utf-8"
            )

            found = scan_legacy_imports(root)
            self.assertEqual(len(found), 5)
            self.assertEqual(
                {item.scope for item in found},
                {
                    "canonical_package",
                    "legacy_package",
                    "test",
                    "tool",
                    "production_or_other",
                },
            )
            forbidden = forbidden_production_imports(found)
            self.assertEqual([item.path for item in forbidden], ["testamur/bad.py"])
            legacy_internal = next(item for item in found if item.path == "witness/old.py")
            self.assertEqual(legacy_internal.recommended_action, MigrationAction.DELETE)
            self.assertFalse(legacy_internal.release_blocking)
            canonical_reverse = forbidden[0]
            self.assertEqual(canonical_reverse.recommended_action, MigrationAction.MIGRATE)
            self.assertTrue(canonical_reverse.release_blocking)

    def test_report_is_machine_readable_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "tests" / "z.py").write_text("import witness.z\n", encoding="utf-8")
            (root / "tests" / "a.py").write_text("import witness.a\n", encoding="utf-8")
            report = legacy_import_report(root)
            self.assertEqual(report["schema"], "testamur.legacy-import-report.v2")
            self.assertEqual(report["total"], 2)
            self.assertEqual(report["release_blocking"], 0)
            self.assertEqual(report["by_action"], {"migrate": 2})
            self.assertEqual(
                [item["path"] for item in report["imports"]],
                ["tests/a.py", "tests/z.py"],
            )
            self.assertEqual(
                {item["recommended_action"] for item in report["imports"]},
                {"migrate"},
            )

    def test_legacy_module_scanner_distinguishes_shim_from_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "witness"
            legacy.mkdir()
            (legacy / "shim.py").write_text(
                '"""compat"""\nfrom testamur.model import canonical_hash\n__all__ = ["canonical_hash"]\n',
                encoding="utf-8",
            )
            (legacy / "implementation.py").write_text(
                "def legacy_logic():\n    return 1\n",
                encoding="utf-8",
            )
            modules = {item.path: item for item in scan_legacy_modules(root)}
            self.assertEqual(modules["witness/shim.py"].state, LegacyModuleState.SHIM)
            self.assertEqual(
                modules["witness/implementation.py"].state,
                LegacyModuleState.IMPLEMENTATION,
            )
            self.assertTrue(modules["witness/implementation.py"].deletion_blocking)

    def test_namespace_deletion_readiness_requires_zero_consumers_and_only_shims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "witness"
            tests = root / "tests"
            legacy.mkdir()
            tests.mkdir()
            shim = legacy / "model.py"
            shim.write_text(
                "from testamur.model import canonical_hash\n__all__ = ['canonical_hash']\n",
                encoding="utf-8",
            )

            ready = legacy_namespace_readiness(root)
            self.assertTrue(ready["ready_to_delete"])
            self.assertEqual(ready["consumer_import_count"], 0)
            self.assertEqual(ready["implementation_module_count"], 0)
            self.assertTrue(ready["deletion_criteria"]["historical_ids_may_remain"])

            implementation = legacy / "engine.py"
            implementation.write_text("def run():\n    return True\n", encoding="utf-8")
            blocked_by_code = legacy_namespace_readiness(root)
            self.assertFalse(blocked_by_code["ready_to_delete"])
            self.assertEqual(blocked_by_code["implementation_module_count"], 1)

            implementation.unlink()
            (tests / "compat.py").write_text("import witness.model\n", encoding="utf-8")
            blocked_by_consumer = legacy_namespace_readiness(root)
            self.assertFalse(blocked_by_consumer["ready_to_delete"])
            self.assertEqual(blocked_by_consumer["consumer_import_count"], 1)

    def test_current_canonical_package_has_no_reverse_witness_import(self) -> None:
        forbidden = forbidden_production_imports(scan_legacy_imports(ROOT))
        self.assertEqual(
            forbidden,
            [],
            "canonical Testamur code must not depend back on the legacy Witness namespace",
        )


if __name__ == "__main__":
    unittest.main()
