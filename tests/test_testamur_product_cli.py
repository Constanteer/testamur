from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
import tempfile
import unittest
from pathlib import Path

from testamur.environment import initialize
from testamur.front_router import main as front_main
from testamur.product_extensions import ProductExtensions
from testamur.product_service import TestamurProductService
from testamur.product_cli import (
    EXIT_CAPABILITY_UNAVAILABLE,
    EXIT_OK,
    EXIT_USAGE,
    _database_path,
    dispatch,
)


class _Service:
    def status(self):
        return {"ok": True, "schema": "testamur.product.status.v1"}

    def get_object(self, ref):
        return {"ok": True, "schema": "testamur.product.object.v1", "ref": ref}

    def history(self, ref, *, limit=50):
        return {"ok": True, "ref": ref, "limit": limit}

    def compare(self, left, right):
        return {"ok": True, "left": left, "right": right}

    def impact(self, ref):
        return {
            "ok": False,
            "schema": "testamur.error.v1",
            "error": {"code": "impact_capability_unavailable", "message": "explicit context required"},
        }

    def temporal(self, ref, query):
        return {"ok": True, "ref": ref, "query": query}

    def temporal_events(self, ref, query):
        return {"ok": True, "schema": "testamur.product.temporal-events.v1", "ref": ref, "query": query}


class ProductCliTest(unittest.TestCase):
    def _run(self, argv):
        output = io.StringIO()
        code = dispatch(argv, stdout=output, service=_Service())
        return code, json.loads(output.getvalue())

    def test_status_is_one_machine_json_object(self):
        code, payload = self._run(["status"])
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(payload["schema"], "testamur.product.status.v1")

    def test_capability_absence_has_stable_nonzero_exit(self):
        code, payload = self._run(["impact", "tst:record:x"])
        self.assertEqual(code, EXIT_CAPABILITY_UNAVAILABLE)
        self.assertEqual(payload["error"]["code"], "impact_capability_unavailable")

    def test_temporal_cli_requires_explicit_semantic_mode(self):
        code, payload = self._run(
            ["temporal", "tst:record:x", "--clause", "KNOWN_AT=2026-01-01T00:00:00Z"]
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(payload["query"]["clauses"][0]["mode"], "known_at")
        self.assertNotIn("as_of", payload["query"])

    def test_ambiguous_temporal_clause_is_rejected(self):
        code, payload = self._run(
            ["temporal", "tst:record:x", "--clause", "AS_OF=2026-01-01T00:00:00Z"]
        )
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(payload["error"]["code"], "invalid_product_request")

    def test_temporal_events_cli_preserves_distinct_recorded_and_event_time_cuts(self):
        code, payload = self._run(
            [
                "temporal-events",
                "tst:record:x",
                "--event-kind",
                "late_observation",
                "--event-kind",
                "retrospective_correction",
                "--recorded-by",
                "2026-01-01T00:00:00Z",
                "--event-time-by",
                "2020-01-01T00:00:00Z",
                "--perspective",
                "node:A",
                "--limit",
                "42",
            ]
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(payload["schema"], "testamur.product.temporal-events.v1")
        self.assertEqual(
            payload["query"]["event_kinds"],
            ["late_observation", "retrospective_correction"],
        )
        self.assertEqual(payload["query"]["recorded_by"], "2026-01-01T00:00:00Z")
        self.assertEqual(payload["query"]["event_time_by"], "2020-01-01T00:00:00Z")
        self.assertEqual(payload["query"]["perspective"], "node:A")
        self.assertEqual(payload["query"]["limit"], 42)
        self.assertNotIn("as_of", payload["query"])

    def test_temporal_query_error_maps_to_usage_exit(self):
        service = _Service()
        service.temporal = lambda ref, query: {
            "ok": False,
            "schema": "testamur.error.v1",
            "error": {"code": "invalid_temporal_query", "message": "multiple perspectives"},
        }
        output = io.StringIO()
        code = dispatch(
            ["temporal", "tst:record:x", "--clause", "KNOWN_AT=2026-01-01T00:00:00Z"],
            stdout=output,
            service=service,
        )
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "invalid_temporal_query")

    def test_project_and_monitor_cli_use_container_model(self):
        with tempfile.TemporaryDirectory() as raw:
            service = TestamurProductService(Path(raw) / "testamur.sqlite3")

            output = io.StringIO()
            code = dispatch(
                [
                    "project", "create", "cli-demo",
                    "--description", "CLI project",
                    "--visibility", "private",
                ],
                stdout=output,
                service=service,
            )
            self.assertEqual(code, EXIT_OK)
            project = json.loads(output.getvalue())
            project_id = project["project_ref"]
            self.assertTrue(project["semantics"]["project_is_container"])

            output = io.StringIO()
            code = dispatch(
                [
                    "monitor", "add",
                    "--project", project_id,
                    "--locator", "https://example.invalid/cli-monitor",
                    "--label", "CLI monitor",
                ],
                stdout=output,
                service=service,
            )
            self.assertEqual(code, EXIT_OK)
            monitor = json.loads(output.getvalue())
            self.assertEqual(monitor["project_id"], project_id)

            output = io.StringIO()
            code = dispatch(
                ["monitor", "list", "--project", project_id],
                stdout=output,
                service=service,
            )
            self.assertEqual(code, EXIT_OK)
            listed = json.loads(output.getvalue())
            self.assertEqual(len(listed["monitors"]), 1)
            self.assertEqual(listed["monitors"][0]["label"], "CLI monitor")

    def test_empty_project_can_exist_without_a_source(self):
        with tempfile.TemporaryDirectory() as raw:
            service = TestamurProductService(Path(raw) / "testamur.sqlite3")
            output = io.StringIO()
            code = dispatch(["project", "create", "empty-project"], stdout=output, service=service)
            self.assertEqual(code, EXIT_OK)
            project = json.loads(output.getvalue())
            self.assertEqual(service.sources.stats()["sources"], 0)
            self.assertEqual(service.watches.stats()["watches"], 0)
            self.assertEqual(service.project(project["project_ref"])["monitors"], [])

    def test_cli_plugin_monitor_provider_uses_provider_config(self):
        with tempfile.TemporaryDirectory() as raw:
            database = Path(raw) / "testamur.sqlite3"
            extensions = ProductExtensions(
                object_readers={},
                monitor_target_providers={
                    "fixture": lambda config: {
                        "locator": f"https://example.invalid/{config['target']}"
                    }
                },
            )
            service = TestamurProductService(database, extensions=extensions)

            output = io.StringIO()
            code = dispatch(
                ["project", "create", "plugin-cli"],
                stdout=output,
                service=service,
            )
            self.assertEqual(code, EXIT_OK)
            project_id = json.loads(output.getvalue())["project_ref"]

            output = io.StringIO()
            code = dispatch(
                [
                    "monitor", "add",
                    "--project", project_id,
                    "--provider", "fixture",
                    "--provider-config", '{"target":"from-cli"}',
                    "--label", "Plugin CLI",
                ],
                stdout=output,
                service=service,
            )
            self.assertEqual(code, EXIT_OK)
            monitor = json.loads(output.getvalue())
            self.assertEqual(monitor["provider"], "fixture")
            self.assertEqual(
                service.project(project_id)["monitors"][0]["locator"],
                "https://example.invalid/from-cli",
            )

    def test_cli_auto_discovers_codex_monitor_provider_manifest(self):
        with tempfile.TemporaryDirectory() as raw:
            database = Path(raw) / "testamur.sqlite3"

            output = io.StringIO()
            code = dispatch(
                [
                    "--database", str(database),
                    "project", "create", "auto-provider",
                ],
                stdout=output,
            )
            self.assertEqual(code, EXIT_OK)
            project_id = json.loads(output.getvalue())["project_ref"]

            output = io.StringIO()
            code = dispatch(
                [
                    "--database", str(database),
                    "monitor", "add",
                    "--project", project_id,
                    "--provider", "github_branch",
                    "--provider-config", '{"repository":"Constanteer/Mathub","branch":"main"}',
                    "--label", "Mathub main",
                ],
                stdout=output,
            )
            self.assertEqual(code, EXIT_OK)
            monitor = json.loads(output.getvalue())
            self.assertEqual(monitor["provider"], "github_branch")

            service = TestamurProductService(database)
            detail = service.project(project_id)
            self.assertEqual(
                detail["monitors"][0]["locator"],
                "https://github.com/Constanteer/Mathub/commits/main.atom",
            )

    def test_top_level_project_and_monitor_commands_route_without_product_prefix(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            initialize(root, name="top-level-cli")
            previous = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with redirect_stdout(output):
                    code = front_main(["project", "create", "top-level"])
                self.assertEqual(code, EXIT_OK)
                project = json.loads(output.getvalue())
                project_id = project["project_ref"]

                output = io.StringIO()
                with redirect_stdout(output):
                    code = front_main([
                        "monitor", "add",
                        "--project", project_id,
                        "--locator", "https://example.invalid/top-level",
                    ])
                self.assertEqual(code, EXIT_OK)
                monitor = json.loads(output.getvalue())
                self.assertEqual(monitor["project_id"], project_id)
            finally:
                os.chdir(previous)

    def test_default_database_discovers_canonical_environment_store(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            environment = initialize(root, name="product-cli")
            nested = root / "nested" / "deeper"
            nested.mkdir(parents=True)
            previous = Path.cwd()
            try:
                os.chdir(nested)
                self.assertEqual(_database_path(None), environment.database_path)
            finally:
                os.chdir(previous)

    def test_explicit_database_path_wins_over_environment_discovery(self):
        explicit = Path("somewhere/custom.sqlite3")
        self.assertEqual(_database_path(str(explicit)), explicit)


if __name__ == "__main__":
    unittest.main()
