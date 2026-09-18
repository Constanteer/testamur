from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.record_source import create_record_from_source_revision
from testamur.record_store import TestamurRecordStore
from testamur.source_store import TestamurSourceStore


class TestamurRecordSourceBridgeTest(unittest.TestCase):
    def test_create_record_pins_existing_revision_snapshot_and_region(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            records = TestamurRecordStore(db)
            source = sources.get_or_create_source("https://example.com/policy")
            snapshot = sources.record_snapshot(
                source["source_id"],
                content=b"The system retains logs for 30 days.",
                observed_at="2026-09-13T12:00:00Z",
            )

            created = create_record_from_source_revision(
                records,
                sources,
                source_revision_id=snapshot["revision_id"],
                snapshot_id=snapshot["snapshot_id"],
                region={"kind": "section", "value": "4.2"},
                statement="Logs are retained for 30 days.",
                title="Retention period",
            )

            revision = created["revision"]
            basis = revision["basis"][0]
            self.assertEqual(basis["ref"], snapshot["revision_id"])
            self.assertEqual(basis["source_ref"], source["source_id"])
            self.assertEqual(basis["snapshot_ref"], snapshot["snapshot_id"])
            self.assertEqual(basis["region"], {"kind": "section", "value": "4.2"})
            self.assertEqual(basis["content_hash"], snapshot["content_hash"])
            self.assertFalse(created["source_binding"]["semantics"]["record_statement_is_source_bytes"])
            self.assertTrue(created["source_binding"]["semantics"]["snapshot_revision_consistency_checked"])
            self.assertFalse(created["source_binding"]["semantics"]["region_semantics_inferred"])

    def test_missing_source_revision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            records = TestamurRecordStore(db)
            with self.assertRaises(KeyError):
                create_record_from_source_revision(
                    records,
                    sources,
                    source_revision_id="tst:revision:missing",
                    statement="claim",
                )

    def test_snapshot_must_belong_to_exact_pinned_revision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            records = TestamurRecordStore(db)
            source = sources.get_or_create_source("https://example.com/policy")
            old = sources.record_snapshot(source["source_id"], content=b"old")
            new = sources.record_snapshot(source["source_id"], content=b"new")

            with self.assertRaises(ValueError):
                create_record_from_source_revision(
                    records,
                    sources,
                    source_revision_id=old["revision_id"],
                    snapshot_id=new["snapshot_id"],
                    statement="claim",
                )

    def test_snapshot_from_different_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            records = TestamurRecordStore(db)
            source_a = sources.get_or_create_source("https://example.com/a")
            source_b = sources.get_or_create_source("https://example.com/b")
            a = sources.record_snapshot(source_a["source_id"], content=b"same")
            b = sources.record_snapshot(source_b["source_id"], content=b"same")

            with self.assertRaises(ValueError):
                create_record_from_source_revision(
                    records,
                    sources,
                    source_revision_id=a["revision_id"],
                    snapshot_id=b["snapshot_id"],
                    statement="claim",
                )


if __name__ == "__main__":
    unittest.main()
