from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.product_service import TestamurProductService
from testamur.web_app import WEB_ROOT, _host_allowed, dispatch_api, dispatch_api_write, dispatch_web_get


class _FakeProductService:
    def status(self):
        return {"ok": True, "schema": "testamur.product.status.v1", "sources": {"count": 1}}

    def dashboard(self, *, limit=30):
        return {
            "ok": True,
            "schema": "testamur.product.dashboard.v1",
            "projects": [],
            "feed": [],
            "watches": [],
            "alerts": [],
            "records": [],
            "status": self.status(),
            "limit": limit,
        }

    def project(self, ref):
        return {
            "ok": True,
            "schema": "testamur.product.project.v2",
            "project": {"project_id": "prj_fake", "slug": ref, "name": "Fake", "visibility": "private"},
            "monitors": [],
        }

    def get_object(self, ref):
        return {
            "ok": True,
            "schema": "testamur.product.object.v1",
            "object": {"kind": "source", "ref": ref, "durable": True},
            "data": {"source_id": ref},
        }

    def history(self, ref, *, limit=50):
        return {"ok": True, "schema": "testamur.product.history.v1", "object": {"ref": ref}, "items": [], "limit": limit}

    def compare(self, left, right):
        return {"ok": True, "schema": "testamur.product.compare.v1", "left": {"ref": left}, "right": {"ref": right}}

    def impact(self, ref):
        return {"ok": False, "schema": "testamur.error.v1", "error": {"code": "impact_capability_unavailable", "message": ref}}

    def temporal(self, ref, query):
        return {"ok": True, "schema": "testamur.temporal.query.v1", "ref": ref, "query": query}

    def temporal_events(self, ref, query):
        return {"ok": True, "schema": "testamur.temporal.events.v1", "ref": ref, "query": query}


class TestamurCanonicalWebTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = _FakeProductService()

    def test_static_surface_is_packaged_under_testamur_namespace(self) -> None:
        self.assertTrue((WEB_ROOT / "index.html").is_file())
        self.assertTrue((WEB_ROOT / "app.js").is_file())
        self.assertTrue((WEB_ROOT / "styles.css").is_file())
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn("Testamur", html)
        self.assertIn("Projects", app)
        self.assertIn("Recent records", app)
        self.assertNotIn("data-add-monitor", app)
        self.assertNotIn("data-new-project-modal", app)
        self.assertIn("environment-chip", app)
        self.assertIn(".primary-nav a.active", styles)
        self.assertIn("/settings/security", app)
        self.assertIn("/v1/account/sessions", app)
        self.assertIn("/v1/account/password", app)
        self.assertIn("/v1/account/delete", app)
        self.assertIn("publicProfilePage", app)
        self.assertIn("data-password-change", app)
        self.assertIn("data-delete-account", app)
        self.assertIn("/settings/organizations", app)
        self.assertIn("/v1/account/workspace", app)
        self.assertIn("data-workspace-id", app)
        self.assertIn("data-create-organization", app)
        self.assertIn("data-org-invite", app)
        self.assertIn(".danger-zone", styles)
        self.assertIn(".workspace-option", styles)
        self.assertIn(".organization-list", styles)
        self.assertIn("projectPage", app)
        self.assertIn("Project overview", app)
        self.assertIn("Source overview", app)
        self.assertIn("Sources are not Projects", app)
        self.assertIn("newProjectPage", app)
        self.assertIn("/projects/new", app)
        self.assertIn("data-add-project-monitor", app)
        self.assertIn("/v1/monitors/refresh", app)
        self.assertIn("data-refresh-monitor", app)
        self.assertIn("/v1/projects/refresh", app)
        self.assertIn("data-refresh-project", app)
        self.assertIn("refreshProjectMonitorsFromButton", app)
        self.assertIn("/v1/monitors/run-due", app)
        self.assertIn("runDueMonitorsFromButton", app)
        self.assertIn('name="interval"', app)
        self.assertIn("cadenceLabel", app)
        self.assertIn("refreshMonitorFromButton", app)
        self.assertIn("monitor_target_providers", app)
        self.assertIn("monitor_target_provider_specs", app)
        self.assertIn("data-provider-field", app)
        self.assertIn("provider-field-help", styles)
        self.assertNotIn("Provider config (JSON)", app)
        self.assertIn(".visibility-options", styles)
        self.assertIn(".new-project-page", styles)
        self.assertIn(
            "async function bootstrap() {\n  await loadAccountState();\n  await render();\n}\n\nbootstrap();",
            app,
        )
        navigate = app.split("function navigate(path) {", 1)[1].split("function bindNavigation()", 1)[0]
        self.assertNotIn("loadAccountState", navigate)
        self.assertIn("render();", navigate)

    def test_workspace_routes_serve_spa_and_unknown_static_path_does_not(self) -> None:
        for path in ("/", "/projects", "/projects/new", "/projects/demo", "/explore", "/monitoring", "/status", "/object/tst%3Asource%3Aone"):
            with self.subTest(path=path):
                response = dispatch_web_get(self.service, path)
                self.assertEqual(response["status"], 200)
                self.assertIn(b"Testamur", response["body"])
        self.assertEqual(dispatch_web_get(self.service, "/../../README.md")["status"], 404)

    def test_dashboard_route_delegates_to_product_service_projection(self) -> None:
        response = dispatch_api(self.service, "/v1/dashboard?limit=10")
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["body"]["schema"], "testamur.product.dashboard.v1")
        self.assertEqual(response["body"]["limit"], 10)

        invalid = dispatch_api(self.service, "/v1/dashboard?bogus=yes")
        self.assertEqual(invalid["status"], 400)
        self.assertEqual(invalid["body"]["error"]["code"], "invalid_argument")

    def test_project_and_monitor_write_routes_use_canonical_stores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = TestamurProductService(Path(tmp) / "testamur.sqlite3")
            project = dispatch_api_write(
                service,
                "/v1/projects",
                {
                    "name": "Demo Project",
                    "description": "Container with multiple monitors",
                    "visibility": "private",
                },
            )
            self.assertEqual(project["status"], 200)
            self.assertTrue(project["body"]["created"])
            project_id = project["body"]["project_ref"]
            self.assertTrue(project_id.startswith("prj_"))
            self.assertTrue(project["body"]["semantics"]["project_is_container"])
            self.assertFalse(project["body"]["semantics"]["project_is_source_presentation"])

            first = dispatch_api_write(
                service,
                "/v1/monitors",
                {
                    "project_id": project_id,
                    "locator": "https://example.invalid/one",
                    "label": "First",
                    "alert_on": ["changed", "unavailable", "recovered"],
                },
            )
            second = dispatch_api_write(
                service,
                "/v1/monitors",
                {
                    "project_id": project_id,
                    "locator": "https://example.invalid/two",
                    "label": "Second",
                    "alert_on": ["changed"],
                },
            )
            self.assertEqual(first["status"], 200)
            self.assertEqual(second["status"], 200)
            self.assertEqual(first["body"]["project_id"], project_id)
            self.assertNotEqual(first["body"]["watch"]["watch_id"], second["body"]["watch"]["watch_id"])

            detail = dispatch_api(service, f"/v1/project?ref={project_id}")
            self.assertEqual(detail["status"], 200)
            self.assertEqual(len(detail["body"]["monitors"]), 2)

            dashboard = service.dashboard(limit=20)
            shown = next(item for item in dashboard["projects"] if item["ref"] == project_id)
            self.assertEqual(shown["monitor_count"], 2)


    def test_write_routes_reject_extra_fields_and_invalid_monitor_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = TestamurProductService(Path(tmp) / "testamur.sqlite3")
            invalid_project = dispatch_api_write(
                service,
                "/v1/projects",
                {"name": "Project", "score": 99},
            )
            self.assertEqual(invalid_project["status"], 400)
            self.assertEqual(invalid_project["body"]["error"]["code"], "invalid_argument")

            source = service.sources.get_or_create_source("https://example.invalid/project")
            invalid_monitor = dispatch_api_write(
                service,
                "/v1/monitors",
                {"source_id": source["source_id"], "alert_on": ["truth_changed"]},
            )
            self.assertEqual(invalid_monitor["status"], 400)
            self.assertEqual(invalid_monitor["body"]["error"]["code"], "invalid_monitor")

    def test_object_route_delegates_to_product_service_contract(self) -> None:
        response = dispatch_api(self.service, "/v1/object?ref=tst%3Asource%3Aone")
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["body"]["object"]["ref"], "tst:source:one")

    def test_duplicate_or_missing_parameters_fail_closed(self) -> None:
        duplicate = dispatch_api(self.service, "/v1/object?ref=a&ref=b")
        missing = dispatch_api(self.service, "/v1/object")
        self.assertEqual(duplicate["status"], 400)
        self.assertEqual(missing["status"], 400)
        self.assertEqual(duplicate["body"]["schema"], "testamur.error.v1")

    def test_product_capability_unavailable_maps_to_503_not_truth_verdict(self) -> None:
        response = dispatch_api(self.service, "/v1/impact?ref=tst%3Asource%3Aone")
        self.assertEqual(response["status"], 503)
        self.assertEqual(response["body"]["error"]["code"], "impact_capability_unavailable")

    def test_temporal_route_keeps_explicit_modes(self) -> None:
        response = dispatch_api(
            self.service,
            "/v1/temporal?ref=tst%3Asource%3Aone&clause=KNOWN_AT%3D2026-09-17T12%3A00%3A00Z",
        )
        self.assertEqual(response["status"], 200)
        clauses = response["body"]["query"]["clauses"]
        self.assertEqual(clauses, [{"mode": "known_at", "at": "2026-09-17T12:00:00Z"}])

    def test_local_host_boundary_rejects_dns_rebinding_names(self) -> None:
        self.assertTrue(_host_allowed("127.0.0.1:8787", "127.0.0.1"))
        self.assertTrue(_host_allowed("localhost:8787", "127.0.0.1"))
        self.assertFalse(_host_allowed("attacker.example:8787", "127.0.0.1"))

    def test_web_module_has_no_legacy_runtime_dependency(self) -> None:
        source = Path(__file__).parents[1] / "testamur" / "web_app.py"
        text = source.read_text(encoding="utf-8")
        self.assertNotIn("from witness", text)
        self.assertNotIn("public_api", text)
        self.assertNotIn("read_service", text)
        self.assertIn("TestamurProductService", text)


if __name__ == "__main__":
    unittest.main()
