from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from testamur.monitor_provider_manifest import load_monitor_provider_registry


class MonitorProviderManifestTest(unittest.TestCase):
    def test_declarative_provider_resolves_https_locator(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / "providers.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "testamur.monitor-providers.v1",
                        "providers": [
                            {
                                "name": "fixture_branch",
                                "label": "Fixture branch",
                                "description": "Fixture provider",
                                "locator_template": "https://example.invalid/{repository}/commits/{branch}.atom",
                                "fields": {
                                    "repository": {
                                        "type": "string",
                                        "required": True,
                                        "pattern": "^[a-z0-9-]+/[a-z0-9-]+$",
                                    },
                                    "branch": {
                                        "type": "string",
                                        "required": True,
                                        "pattern": "^[a-z0-9._-]+$",
                                    },
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            registry = load_monitor_provider_registry([manifest], include_defaults=False)
            self.assertIn("fixture_branch", registry.providers)
            self.assertEqual(registry.errors, ())
            resolved = registry.providers["fixture_branch"](
                {"repository": "owner/repo", "branch": "main"}
            )
            self.assertEqual(
                resolved["locator"],
                "https://example.invalid/owner/repo/commits/main.atom",
            )
            spec = registry.specs["fixture_branch"]
            self.assertEqual(spec["label"], "Fixture branch")
            self.assertTrue(spec["fields"]["repository"]["required"])

    def test_invalid_manifest_fails_closed_without_registering_provider(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest = Path(raw) / "bad.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "testamur.monitor-providers.v1",
                        "providers": [
                            {
                                "name": "bad",
                                "locator_template": "file:///{path}",
                                "fields": {"path": {"type": "string", "required": True}},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            registry = load_monitor_provider_registry([manifest], include_defaults=False)
            self.assertNotIn("bad", registry.providers)
            self.assertTrue(registry.errors)
            self.assertIn("absolute HTTPS", registry.errors[0])


if __name__ == "__main__":
    unittest.main()
