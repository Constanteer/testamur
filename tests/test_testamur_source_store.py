from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from testamur.source_store import TestamurSourceStore


class TestamurSourceStoreTest(unittest.TestCase):
    def test_same_bytes_reuse_revision_but_create_distinct_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            source = store.get_or_create_source("https://example.com/spec")

            first = store.record_snapshot(
                source["source_id"],
                content=b"version one\n",
                observed_at="2026-09-13T10:00:00Z",
            )
            second = store.record_snapshot(
                source["source_id"],
                content=b"version one\n",
                observed_at="2026-09-13T11:00:00Z",
            )

            self.assertEqual(first["revision_id"], second["revision_id"])
            self.assertNotEqual(first["snapshot_id"], second["snapshot_id"])
            self.assertEqual(first["content_hash"], second["content_hash"])
            self.assertTrue(first["semantics"]["same_revision_may_have_multiple_snapshots"])
            self.assertFalse(first["semantics"]["snapshot_is_revision_identity"])

            history = store.history(source["source_id"])
            self.assertEqual(len(history), 2)
            self.assertEqual(
                {item["snapshot_id"] for item in history},
                {first["snapshot_id"], second["snapshot_id"]},
            )
            by_revision = store.snapshots_for_revision(first["revision_id"])
            self.assertEqual(len(by_revision), 2)

    def test_changed_bytes_create_new_revision_without_mutating_old_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            source = store.get_or_create_source("https://example.com/policy")
            old = store.record_snapshot(
                source["source_id"],
                content=b"old\n",
                observed_at="2026-09-12T10:00:00Z",
            )
            new = store.record_snapshot(
                source["source_id"],
                content=b"new\n",
                observed_at="2026-09-13T10:00:00Z",
            )

            self.assertNotEqual(old["revision_id"], new["revision_id"])
            self.assertNotEqual(old["content_hash"], new["content_hash"])
            self.assertEqual(store.get_snapshot(old["snapshot_id"]), old)
            self.assertEqual(
                store.get_revision(old["revision_id"])["content_hash"],
                old["content_hash"],
            )

            compared = store.compare_snapshots(old["snapshot_id"], new["snapshot_id"])
            self.assertTrue(compared["content_identity_assessable"])
            self.assertTrue(compared["content_changed"])
            self.assertFalse(compared["same_revision"])
            self.assertFalse(compared["semantics"]["semantic_change_inferred"])

    def test_metadata_only_snapshot_has_no_revision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            source = store.get_or_create_source("https://example.com/unavailable")
            snapshot = store.record_snapshot(
                source["source_id"],
                status="unavailable",
                retrieval_metadata={"http_status": 503},
                observed_at="2026-09-13T12:00:00Z",
            )
            self.assertIsNone(snapshot["revision_id"])
            self.assertIsNone(snapshot["content_hash"])
            self.assertEqual(snapshot["digest_basis"], "not_available")
            self.assertEqual(snapshot["retrieval_metadata"]["http_status"], 503)

    def test_captured_status_requires_exact_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            source = store.get_or_create_source("https://example.com/a")
            with self.assertRaises(ValueError):
                store.record_snapshot(source["source_id"], status="captured")

    def test_declared_digest_must_be_sha256_and_match_supplied_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            source = store.get_or_create_source("https://example.com/spec")
            for bad in (
                "md5:abc",
                "sha256:abc123",
                "sha256:" + "z" * 64,
            ):
                with self.subTest(bad=bad):
                    with self.assertRaises(ValueError):
                        store.record_snapshot(source["source_id"], content_hash=bad)

            wrong_valid_sha = "sha256:" + "0" * 64
            with self.assertRaises(ValueError):
                store.record_snapshot(
                    source["source_id"],
                    content=b"exact bytes",
                    content_hash=wrong_valid_sha,
                )

    def test_declared_digest_is_explicitly_distinguished_from_computed_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            source = store.get_or_create_source("https://example.com/hash-only")
            digest = "sha256:" + hashlib.sha256(b"external bytes").hexdigest()
            snapshot = store.record_snapshot(
                source["source_id"],
                content_hash=digest.upper().replace("SHA256:", "sha256:"),
            )
            self.assertEqual(snapshot["digest_basis"], "declared_digest")
            self.assertEqual(snapshot["content_hash"], digest)
            revision = store.get_revision(snapshot["revision_id"])
            self.assertIsNotNone(revision)
            self.assertEqual(revision["content_hash"], digest)
            self.assertEqual(revision["identity_semantics"]["digest_algorithm"], "sha256")

    def test_source_identity_is_stable_for_exact_initial_locator(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            first = store.get_or_create_source("https://example.com/a")
            second = store.get_or_create_source("https://example.com/a")
            self.assertEqual(first, second)
            self.assertTrue(first["identity_semantics"]["persistent_identity"])
            self.assertFalse(first["identity_semantics"]["locator_equivalence_inferred"])

    def test_cross_source_compare_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            left_source = store.get_or_create_source("https://example.com/a")
            right_source = store.get_or_create_source("https://example.com/b")
            left = store.record_snapshot(left_source["source_id"], content=b"same")
            right = store.record_snapshot(right_source["source_id"], content=b"same")
            self.assertNotEqual(left["revision_id"], right["revision_id"])
            with self.assertRaises(ValueError):
                store.compare_snapshots(left["snapshot_id"], right["snapshot_id"])

    def test_history_cursor_is_exclusive_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            source = store.get_or_create_source("https://example.com/history")
            created = [
                store.record_snapshot(source["source_id"], content=f"v{i}".encode())
                for i in range(5)
            ]
            first_page = store.history(source["source_id"], limit=2)
            self.assertEqual(len(first_page), 2)
            cursor = (
                first_page[-1]["recorded_at"],
                first_page[-1]["snapshot_id"],
            )
            second_page = store.history(source["source_id"], limit=2, before=cursor)
            self.assertEqual(len(second_page), 2)
            self.assertTrue(
                set(item["snapshot_id"] for item in first_page).isdisjoint(
                    item["snapshot_id"] for item in second_page
                )
            )
            all_seen = first_page + second_page + store.history(
                source["source_id"],
                limit=2,
                before=(second_page[-1]["recorded_at"], second_page[-1]["snapshot_id"]),
            )
            self.assertEqual(
                {item["snapshot_id"] for item in all_seen},
                {item["snapshot_id"] for item in created},
            )

    def test_stats_distinguish_source_revision_snapshot_counts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            source = store.get_or_create_source("https://example.com/stats")
            store.record_snapshot(source["source_id"], content=b"same")
            store.record_snapshot(source["source_id"], content=b"same")
            store.record_snapshot(source["source_id"], status="unavailable")
            stats = store.stats()
            self.assertEqual(stats["sources"], 1)
            self.assertEqual(stats["revisions"], 1)
            self.assertEqual(stats["snapshots"], 3)
            self.assertEqual(stats["snapshots_without_revision"], 1)

    def test_tables_are_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            source = store.get_or_create_source("https://example.com/a")
            snapshot = store.record_snapshot(source["source_id"], content=b"value")

            with self.assertRaises(sqlite3.DatabaseError):
                with store.connect() as conn:
                    conn.execute(
                        "UPDATE testamur_sources SET initial_locator='changed' WHERE source_id=?",
                        (source["source_id"],),
                    )
            with self.assertRaises(sqlite3.DatabaseError):
                with store.connect() as conn:
                    conn.execute(
                        "DELETE FROM testamur_source_snapshots WHERE snapshot_id=?",
                        (snapshot["snapshot_id"],),
                    )

    def test_latest_recorded_snapshot_is_explicitly_not_generic_as_of(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurSourceStore(Path(raw) / "testamur.sqlite3")
            source = store.get_or_create_source("https://example.com/a")
            first = store.record_snapshot(
                source["source_id"],
                content=b"first",
                observed_at="2030-01-01T00:00:00Z",
            )
            second = store.record_snapshot(
                source["source_id"],
                content=b"late discovered older observation",
                observed_at="2020-01-01T00:00:00Z",
            )
            latest = store.latest_recorded_snapshot(source["source_id"])
            # This method follows local recording order. Temporal reconstruction
            # belongs to the explicit KNOWN_AT/AVAILABLE_BY/EFFECTIVE_AT layer.
            self.assertEqual(latest["snapshot_id"], second["snapshot_id"])
            self.assertNotEqual(latest["snapshot_id"], first["snapshot_id"])


if __name__ == "__main__":
    unittest.main()
