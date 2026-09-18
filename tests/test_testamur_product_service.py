from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.product_actions import create_monitor
from testamur.product_extensions import ProductExtensions
from testamur.product_service import TestamurProductService


class TestamurProductServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "testamur.sqlite3"
        self.service = TestamurProductService(self.db)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_source_history_and_mechanical_compare_are_one_surface(self) -> None:
        source = self.service.sources.get_or_create_source("https://example.invalid/spec")
        first = self.service.sources.record_snapshot(source["source_id"], content=b"one")
        second = self.service.sources.record_snapshot(source["source_id"], content=b"two")

        shown = self.service.get_object(source["source_id"])
        self.assertTrue(shown["ok"])
        self.assertEqual(shown["object"]["kind"], "source")

        history = self.service.history(source["source_id"])
        self.assertTrue(history["ok"])
        self.assertEqual(history["item_kind"], "snapshot")
        self.assertEqual(len(history["items"]), 2)

        comparison = self.service.compare(first["snapshot_id"], second["snapshot_id"])
        self.assertTrue(comparison["ok"])
        self.assertTrue(comparison["comparison"]["content_changed"])
        self.assertFalse(comparison["semantics"]["validity_or_truth_change_inferred"])

    def test_record_history_preserves_recorded_not_verified_boundary(self) -> None:
        created = self.service.records.create_record(
            record_kind="claim",
            statement="fixture statement",
        )
        record_id = created["record"]["record_id"]
        revision = created["revision"]
        self.service.records.append_revision(
            record_id,
            expected_parent_revision_id=revision["revision_id"],
            statement="revised fixture statement",
        )
        history = self.service.history(record_id)
        self.assertTrue(history["ok"])
        self.assertEqual(len(history["items"]), 2)
        self.assertTrue(history["semantics"]["history_is_recorded_history"])

    def test_dashboard_projects_are_containers_with_many_monitors(self) -> None:
        project = self.service.projects.create_project(
            name="Dashboard Project",
            description="Two monitored inputs",
            visibility="private",
        )
        sources = [
            self.service.sources.get_or_create_source("https://example.invalid/dashboard-a"),
            self.service.sources.get_or_create_source("https://example.invalid/dashboard-b"),
        ]
        watch_ids = []
        for index, source in enumerate(sources, start=1):
            first = self.service.sources.record_snapshot(source["source_id"], content=f"v{index}".encode())
            created = self.service.watches.create_watch(
                self.service.sources,
                source_id=source["source_id"],
                label=f"Monitor {index}",
            )
            watch_id = created["watch"]["watch_id"]
            watch_ids.append(watch_id)
            self.service.projects.link_monitor(
                project_id=project["project_id"],
                watch_id=watch_id,
                source_id=source["source_id"],
            )
            self.service.watches.evaluate_snapshot(
                self.service.sources,
                watch_id=watch_id,
                snapshot_id=first["snapshot_id"],
            )

        second = self.service.sources.record_snapshot(sources[0]["source_id"], content=b"changed")
        changed = self.service.watches.evaluate_snapshot(
            self.service.sources,
            watch_id=watch_ids[0],
            snapshot_id=second["snapshot_id"],
        )

        dashboard = self.service.dashboard(limit=20)
        self.assertTrue(dashboard["ok"])
        self.assertTrue(dashboard["semantics"]["read_projection_only"])
        self.assertTrue(dashboard["semantics"]["projects_are_containers"])
        self.assertFalse(dashboard["semantics"]["project_entries_are_tracked_sources"])
        self.assertTrue(dashboard["semantics"]["monitors_link_projects_to_sources"])

        shown = next(item for item in dashboard["projects"] if item["ref"] == project["project_id"])
        self.assertEqual(shown["name"], "Dashboard Project")
        self.assertEqual(shown["monitor_count"], 2)

        detail = self.service.project(project["project_id"])
        self.assertTrue(detail["ok"])
        self.assertEqual(len(detail["monitors"]), 2)
        self.assertEqual({item["project_id"] for item in detail["monitors"]}, {project["project_id"]})

        monitor = next(item for item in dashboard["watches"] if item["watch_id"] == watch_ids[0])
        self.assertEqual(monitor["project_id"], project["project_id"])
        self.assertEqual(monitor["latest_state"], "changed")
        self.assertIsNotNone(changed["alert"])


    def test_monitor_provider_resolves_target_but_core_owns_watch_and_project_membership(self) -> None:
        project = self.service.projects.create_project(
            name="Plugin Project",
            visibility="private",
        )
        extensions = ProductExtensions(
            object_readers={},
            monitor_target_providers={
                "fixture": lambda config: {
                    "locator": f"https://example.invalid/{config['target']}"
                }
            },
        )
        service = TestamurProductService(self.db, extensions=extensions)
        result = create_monitor(
            service,
            project_id=project["project_id"],
            provider="fixture",
            provider_config={"target": "plugin-monitor"},
            label="Plugin monitor",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "fixture")
        self.assertTrue(result["watch"]["watch_id"].startswith("tst:watch:"))
        detail = service.project(project["project_id"])
        self.assertEqual(len(detail["monitors"]), 1)
        self.assertEqual(
            detail["monitors"][0]["locator"],
            "https://example.invalid/plugin-monitor",
        )
        self.assertEqual(
            service.extensions.capabilities()["monitor_target_providers"],
            ["fixture"],
        )

        missing = create_monitor(
            service,
            project_id=project["project_id"],
            provider="not-installed",
            provider_config={},
        )
        self.assertFalse(missing["ok"])
        self.assertEqual(
            missing["error"]["code"],
            "monitor_provider_unavailable",
        )

    def test_unknown_and_unsupported_refs_use_stable_error_envelope(self) -> None:
        missing = self.service.get_object("tst:source:missing")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["schema"], "testamur.error.v1")
        self.assertEqual(missing["error"]["code"], "object_not_found")

        unsupported = self.service.get_object("tst:policy:fixture")
        self.assertFalse(unsupported["ok"])
        self.assertEqual(unsupported["error"]["code"], "unsupported_object_kind")

    def test_cross_family_compare_is_rejected_without_semantic_guessing(self) -> None:
        result = self.service.compare("tst:snapshot:a", "tst:record-revision:b")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "incompatible_compare")


if __name__ == "__main__":
    unittest.main()
