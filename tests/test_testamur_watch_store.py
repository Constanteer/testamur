from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from testamur.source_store import TestamurSourceStore
from testamur.watch_store import TestamurWatchStore


class TestamurWatchStoreTest(unittest.TestCase):
    def test_watch_tracks_change_unavailable_and_recovery_without_truth_claims(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            watches = TestamurWatchStore(db)
            source = sources.get_or_create_source("https://example.com/spec")
            watch = watches.create_watch(sources, source_id=source["source_id"])
            watch_id = watch["watch"]["watch_id"]

            first = sources.record_snapshot(source["source_id"], content=b"v1")
            initial = watches.evaluate_snapshot(
                sources, watch_id=watch_id, snapshot_id=first["snapshot_id"]
            )
            self.assertEqual(initial["evaluation"]["operational_state"], "initial")
            self.assertIsNone(initial["alert"])

            same = sources.record_snapshot(source["source_id"], content=b"v1")
            unchanged = watches.evaluate_snapshot(
                sources, watch_id=watch_id, snapshot_id=same["snapshot_id"]
            )
            self.assertEqual(unchanged["evaluation"]["operational_state"], "unchanged")
            self.assertIsNone(unchanged["alert"])

            changed_snapshot = sources.record_snapshot(source["source_id"], content=b"v2")
            changed = watches.evaluate_snapshot(
                sources,
                watch_id=watch_id,
                snapshot_id=changed_snapshot["snapshot_id"],
            )
            self.assertEqual(changed["evaluation"]["operational_state"], "changed")
            self.assertEqual(changed["alert"]["event_type"], "changed")
            self.assertFalse(changed["evaluation"]["semantics"]["truth_change_implied"])
            self.assertFalse(changed["alert"]["semantics"]["truth_status_implied"])

            unavailable_snapshot = sources.record_snapshot(
                source["source_id"], status="unavailable"
            )
            unavailable = watches.evaluate_snapshot(
                sources,
                watch_id=watch_id,
                snapshot_id=unavailable_snapshot["snapshot_id"],
            )
            self.assertEqual(
                unavailable["evaluation"]["operational_state"], "unavailable"
            )
            self.assertEqual(unavailable["alert"]["event_type"], "unavailable")

            still_unavailable_snapshot = sources.record_snapshot(
                source["source_id"], status="unavailable"
            )
            still_unavailable = watches.evaluate_snapshot(
                sources,
                watch_id=watch_id,
                snapshot_id=still_unavailable_snapshot["snapshot_id"],
            )
            self.assertEqual(
                still_unavailable["evaluation"]["operational_state"], "unavailable"
            )
            self.assertIsNone(still_unavailable["alert"])

            recovered_snapshot = sources.record_snapshot(source["source_id"], content=b"v2")
            recovered = watches.evaluate_snapshot(
                sources,
                watch_id=watch_id,
                snapshot_id=recovered_snapshot["snapshot_id"],
            )
            self.assertEqual(recovered["evaluation"]["operational_state"], "recovered")
            self.assertEqual(recovered["alert"]["event_type"], "recovered")

            alerts = watches.alerts(watch_id)
            self.assertEqual(
                {item["event_type"] for item in alerts},
                {"changed", "unavailable", "recovered"},
            )

    def test_not_assessable_is_not_treated_as_unavailable_or_false(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            watches = TestamurWatchStore(db)
            source = sources.get_or_create_source("https://example.com/metadata")
            watch_id = watches.create_watch(
                sources, source_id=source["source_id"]
            )["watch"]["watch_id"]
            snapshot = sources.record_snapshot(source["source_id"], status="metadata_only")
            value = watches.evaluate_snapshot(
                sources, watch_id=watch_id, snapshot_id=snapshot["snapshot_id"]
            )
            self.assertEqual(value["evaluation"]["operational_state"], "not_assessable")
            self.assertIsNone(value["alert"])
            self.assertFalse(value["evaluation"]["semantics"]["truth_change_implied"])

    def test_alert_configuration_filters_events_and_is_revisioned(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            watches = TestamurWatchStore(db)
            source = sources.get_or_create_source("https://example.com/spec")
            created = watches.create_watch(
                sources,
                source_id=source["source_id"],
                alert_on=["changed"],
                label="Spec",
            )
            watch_id = created["watch"]["watch_id"]
            self.assertEqual(created["revision"]["alert_on"], ["changed"])

            first = sources.record_snapshot(source["source_id"], content=b"v1")
            watches.evaluate_snapshot(
                sources, watch_id=watch_id, snapshot_id=first["snapshot_id"]
            )
            unavailable = sources.record_snapshot(source["source_id"], status="unavailable")
            value = watches.evaluate_snapshot(
                sources, watch_id=watch_id, snapshot_id=unavailable["snapshot_id"]
            )
            self.assertEqual(value["evaluation"]["event_type"], "unavailable")
            self.assertIsNone(value["alert"])

            next_revision = watches.append_watch_revision(
                watch_id,
                expected_parent_revision_id=created["revision"]["revision_id"],
                alert_on=["changed", "recovered"],
            )
            self.assertEqual(next_revision["ordinal"], 2)
            self.assertEqual(
                next_revision["parent_revision_id"],
                created["revision"]["revision_id"],
            )
            self.assertEqual(next_revision["alert_on"], ["changed", "recovered"])
            self.assertEqual(watches.latest_watch_revision(watch_id), next_revision)

            with self.assertRaises(ValueError):
                watches.append_watch_revision(
                    watch_id,
                    expected_parent_revision_id=created["revision"]["revision_id"],
                    alert_on=["changed"],
                )

    def test_monitor_cadence_is_revisioned_and_manual_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            watches = TestamurWatchStore(db)
            source = sources.get_or_create_source("https://example.com/cadence")

            created = watches.create_watch(
                sources,
                source_id=source["source_id"],
                interval_seconds=900,
            )
            self.assertEqual(created["revision"]["interval_seconds"], 900)
            self.assertTrue(created["revision"]["semantics"]["automatic_refresh_opt_in"])

            preserved = watches.append_watch_revision(
                created["watch"]["watch_id"],
                expected_parent_revision_id=created["revision"]["revision_id"],
                label="Renamed",
            )
            self.assertEqual(preserved["interval_seconds"], 900)

            manual = watches.append_watch_revision(
                created["watch"]["watch_id"],
                expected_parent_revision_id=preserved["revision_id"],
                interval_seconds=None,
            )
            self.assertIsNone(manual["interval_seconds"])
            self.assertFalse(manual["semantics"]["automatic_refresh_opt_in"])

            with self.assertRaises(ValueError):
                watches.create_watch(
                    sources,
                    source_id=source["source_id"],
                    interval_seconds=60,
                )

    def test_same_snapshot_evaluation_is_idempotently_reused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            watches = TestamurWatchStore(db)
            source = sources.get_or_create_source("https://example.com/spec")
            watch_id = watches.create_watch(
                sources, source_id=source["source_id"]
            )["watch"]["watch_id"]
            snapshot = sources.record_snapshot(source["source_id"], status="unavailable")
            first = watches.evaluate_snapshot(
                sources, watch_id=watch_id, snapshot_id=snapshot["snapshot_id"]
            )
            second = watches.evaluate_snapshot(
                sources, watch_id=watch_id, snapshot_id=snapshot["snapshot_id"]
            )
            self.assertFalse(first["reused"])
            self.assertTrue(second["reused"])
            self.assertEqual(
                first["evaluation"]["evaluation_id"],
                second["evaluation"]["evaluation_id"],
            )
            self.assertEqual(first["alert"]["alert_id"], second["alert"]["alert_id"])
            self.assertEqual(watches.stats()["evaluations"], 1)
            self.assertEqual(watches.stats()["alerts"], 1)

    def test_watch_rejects_snapshot_from_another_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            watches = TestamurWatchStore(db)
            source_a = sources.get_or_create_source("https://example.com/a")
            source_b = sources.get_or_create_source("https://example.com/b")
            watch_id = watches.create_watch(
                sources, source_id=source_a["source_id"]
            )["watch"]["watch_id"]
            snapshot_b = sources.record_snapshot(source_b["source_id"], content=b"b")
            with self.assertRaises(ValueError):
                watches.evaluate_snapshot(
                    sources,
                    watch_id=watch_id,
                    snapshot_id=snapshot_b["snapshot_id"],
                )

    def test_unsupported_event_and_missing_source_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            watches = TestamurWatchStore(db)
            with self.assertRaises(KeyError):
                watches.create_watch(sources, source_id="tst:source:missing")
            source = sources.get_or_create_source("https://example.com/a")
            with self.assertRaises(ValueError):
                watches.create_watch(
                    sources,
                    source_id=source["source_id"],
                    alert_on=["source-is-false"],
                )

    def test_watch_tables_are_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            watches = TestamurWatchStore(db)
            source = sources.get_or_create_source("https://example.com/a")
            created = watches.create_watch(sources, source_id=source["source_id"])
            watch_id = created["watch"]["watch_id"]
            snapshot = sources.record_snapshot(source["source_id"], content=b"a")
            evaluation = watches.evaluate_snapshot(
                sources, watch_id=watch_id, snapshot_id=snapshot["snapshot_id"]
            )["evaluation"]

            with self.assertRaises(sqlite3.DatabaseError):
                with watches.connect() as conn:
                    conn.execute(
                        "UPDATE testamur_watches SET source_id='changed' WHERE watch_id=?",
                        (watch_id,),
                    )
            with self.assertRaises(sqlite3.DatabaseError):
                with watches.connect() as conn:
                    conn.execute(
                        "DELETE FROM testamur_watch_evaluations WHERE evaluation_id=?",
                        (evaluation["evaluation_id"],),
                    )


if __name__ == "__main__":
    unittest.main()
