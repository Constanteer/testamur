from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from testamur.record_store import RELATION_TYPES, TestamurRecordStore
from testamur.source_store import TestamurSourceStore


class TestamurRecordStoreTest(unittest.TestCase):
    def test_record_identity_persists_across_append_only_revisions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurRecordStore(Path(raw) / "testamur.sqlite3")
            created = store.create_record(
                record_kind="assertion",
                statement="The system retains logs for 30 days.",
                title="Retention",
            )
            record = created["record"]
            first = created["revision"]
            second = store.append_revision(
                record["record_id"],
                expected_parent_revision_id=first["revision_id"],
                statement="The system retains logs for 45 days.",
            )

            self.assertEqual(first["record_id"], second["record_id"])
            self.assertNotEqual(first["revision_id"], second["revision_id"])
            self.assertEqual(second["parent_revision_id"], first["revision_id"])
            self.assertEqual(second["ordinal"], 2)
            self.assertEqual(store.latest_revision(record["record_id"]), second)
            self.assertTrue(record["identity_semantics"]["persistent_identity"])
            self.assertFalse(first["semantics"]["statement_is_source_bytes"])
            self.assertFalse(first["semantics"]["truth_implied_by_recording"])

    def test_basis_can_pin_exact_source_revision_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "testamur.sqlite3"
            sources = TestamurSourceStore(db)
            source = sources.get_or_create_source("https://example.com/policy")
            snapshot = sources.record_snapshot(source["source_id"], content=b"policy bytes")

            records = TestamurRecordStore(db)
            created = records.create_record(
                record_kind="assertion",
                statement="Normalized assertion distinct from source bytes.",
                basis=[
                    {
                        "kind": "source_revision",
                        "ref": snapshot["revision_id"],
                        "snapshot_ref": snapshot["snapshot_id"],
                        "region": {"section": "4.2"},
                    }
                ],
            )
            basis = created["revision"]["basis"][0]
            self.assertEqual(basis["ref"], snapshot["revision_id"])
            self.assertEqual(basis["snapshot_ref"], snapshot["snapshot_id"])
            self.assertEqual(basis["region"]["section"], "4.2")
            self.assertFalse(
                created["revision"]["semantics"]["basis_entries_have_equal_epistemic_force"]
            )

    def test_stale_expected_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurRecordStore(Path(raw) / "testamur.sqlite3")
            created = store.create_record(record_kind="claim", statement="v1")
            first = created["revision"]
            second = store.append_revision(
                created["record"]["record_id"],
                expected_parent_revision_id=first["revision_id"],
                statement="v2",
            )
            with self.assertRaises(ValueError):
                store.append_revision(
                    created["record"]["record_id"],
                    expected_parent_revision_id=first["revision_id"],
                    statement="conflicting v2",
                )
            self.assertEqual(
                store.latest_revision(created["record"]["record_id"])["revision_id"],
                second["revision_id"],
            )

    def test_revision_comparison_is_mechanical_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurRecordStore(Path(raw) / "testamur.sqlite3")
            created = store.create_record(
                record_kind="requirement",
                statement="Must retain logs.",
                basis=[{"kind": "requirement", "ref": "spec:1"}],
            )
            first = created["revision"]
            second = store.append_revision(
                created["record"]["record_id"],
                expected_parent_revision_id=first["revision_id"],
                statement="Must retain logs for 30 days.",
            )
            compared = store.compare_revisions(first["revision_id"], second["revision_id"])
            self.assertTrue(compared["statement_changed"])
            self.assertFalse(compared["basis_changed"])
            self.assertFalse(compared["semantics"]["semantic_equivalence_inferred"])
            self.assertFalse(compared["semantics"]["truth_change_inferred"])

    def test_relations_are_first_class_immutable_objects(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurRecordStore(Path(raw) / "testamur.sqlite3")
            left = store.create_record(record_kind="claim", statement="A")["revision"]
            right = store.create_record(record_kind="claim", statement="B")["revision"]
            relation = store.create_relation(
                "supports",
                from_ref=left["revision_id"],
                to_ref=right["revision_id"],
                basis=[{"kind": "observation", "ref": "tst:obs:evidence"}],
                created_by="human:alice",
            )
            self.assertIn("supports", RELATION_TYPES)
            self.assertEqual(store.get_relation(relation["relation_id"]), relation)
            self.assertTrue(relation["semantics"]["first_class_immutable_relation"])
            self.assertFalse(relation["semantics"]["relation_implies_truth"])
            self.assertFalse(relation["semantics"]["relation_implies_causality"])

            outgoing = store.relations_for(left["revision_id"], direction="outgoing")
            incoming = store.relations_for(right["revision_id"], direction="incoming")
            self.assertEqual([item["relation_id"] for item in outgoing], [relation["relation_id"]])
            self.assertEqual([item["relation_id"] for item in incoming], [relation["relation_id"]])

    def test_relation_vocabulary_and_filters_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurRecordStore(Path(raw) / "testamur.sqlite3")
            with self.assertRaises(ValueError):
                store.create_relation("ai-says-related", from_ref="a", to_ref="b")
            with self.assertRaises(ValueError):
                store.create_relation("cites", from_ref="same", to_ref="same")

            store.create_relation("cites", from_ref="a", to_ref="b")
            store.create_relation("contradicts", from_ref="a", to_ref="c")
            cited = store.relations_for(
                "a", direction="outgoing", relation_types=["cites"]
            )
            self.assertEqual(len(cited), 1)
            self.assertEqual(cited[0]["relation_type"], "cites")

    def test_store_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurRecordStore(Path(raw) / "testamur.sqlite3")
            created = store.create_record(record_kind="claim", statement="A")
            relation = store.create_relation("cites", from_ref="a", to_ref="b")
            with self.assertRaises(sqlite3.DatabaseError):
                with store.connect() as conn:
                    conn.execute(
                        "UPDATE testamur_record_revisions SET statement='changed' WHERE revision_id=?",
                        (created["revision"]["revision_id"],),
                    )
            with self.assertRaises(sqlite3.DatabaseError):
                with store.connect() as conn:
                    conn.execute(
                        "DELETE FROM testamur_relations WHERE relation_id=?",
                        (relation["relation_id"],),
                    )

    def test_stats_keep_identity_revision_relation_counts_separate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurRecordStore(Path(raw) / "testamur.sqlite3")
            created = store.create_record(record_kind="claim", statement="A")
            store.append_revision(
                created["record"]["record_id"],
                expected_parent_revision_id=created["revision"]["revision_id"],
                statement="A2",
            )
            store.create_relation("cites", from_ref="a", to_ref="b")
            stats = store.stats()
            self.assertEqual(stats["records"], 1)
            self.assertEqual(stats["record_revisions"], 2)
            self.assertEqual(stats["relations"], 1)


if __name__ == "__main__":
    unittest.main()
