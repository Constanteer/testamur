from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from testamur.revision_assurance import TestamurVersionedStore
from testamur.revision_store import TestamurRevisionStore
from testamur.store import LegacyGraphStore, TestamurStore
from testamur.store_lifecycle import ClosingConnection


class TestamurStoreNamespaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "legacy-graph.sqlite3"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_store_ownership_is_testamur_only(self) -> None:
        self.assertIs(TestamurStore, LegacyGraphStore)
        self.assertEqual(TestamurStore.__name__, "TestamurStore")
        self.assertEqual(TestamurStore.__module__, "testamur.store")
        self.assertEqual(TestamurRevisionStore.__name__, "TestamurRevisionStore")
        self.assertNotIn("Witness", TestamurRevisionStore.__mro__[1].__name__)
        self.assertTrue(issubclass(TestamurVersionedStore, TestamurStore))
        self.assertTrue(TestamurVersionedStore.__module__.startswith("testamur."))

    def test_new_graph_writes_use_testamur_identity(self) -> None:
        store = TestamurStore(self.path)
        project = store.create_project("identity", "Identity")
        claim = store.create_object(project["id"], "claim", {"value": 1})
        verifier = store.create_object(project["id"], "verifier", {"tool": "fixture"})
        evidence = store.create_object(project["id"], "evidence", {"digest": "sha256:a"})
        edge = store.add_edge(project["id"], claim["id"], evidence["id"], "depends_on")
        run = store.record_verification(project["id"], claim["id"], verifier["id"], "tested")
        revised = store.revise_object(evidence["id"], {"digest": "sha256:b"})
        self.assertTrue(project["id"].startswith("tpr_"))
        self.assertTrue(claim["id"].startswith("tob_"))
        self.assertTrue(claim["revision_id"].startswith("trv_"))
        self.assertTrue(revised["revision_id"].startswith("trv_"))
        self.assertTrue(edge["id"].startswith("ted_"))
        self.assertTrue(run["id"].startswith("tvr_"))

    def test_canonical_connection_context_commits_or_rolls_back_then_closes(self) -> None:
        store = TestamurStore(self.path)
        with store.connect() as conn:
            self.assertIsInstance(conn, ClosingConnection)
            conn.execute("SELECT 1").fetchone()
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_base_write_reopens_through_canonical_versioned_store_without_data_migration(self) -> None:
        store = TestamurStore(self.path)
        project = store.create_project("namespace", "Namespace")
        claim = store.create_object(project["id"], "claim", {"value": 1})
        verifier = store.create_object(project["id"], "verifier", {"tool": "fixture"})
        evidence = store.create_object(project["id"], "evidence", {"digest": "sha256:a"})
        edge = store.add_edge(project["id"], claim["id"], evidence["id"], "depends_on")
        run = store.record_verification(project["id"], claim["id"], verifier["id"], "tested", input_object_ids=[evidence["id"]], result={"ok": True})
        reopened = TestamurVersionedStore(self.path)
        self.assertEqual(reopened.get_project(project["id"])["id"], project["id"])
        self.assertEqual(reopened.get_object(claim["id"])["revision_id"], claim["revision_id"])
        self.assertEqual(reopened.list_edges(project["id"])[0]["id"], edge["id"])
        self.assertFalse(reopened.get_verification_run(run["id"])["stale"])
        reopened.revise_object(evidence["id"], {"digest": "sha256:b"})
        checked = TestamurStore(self.path).get_verification_run(run["id"])
        self.assertTrue(checked["stale"])
        self.assertEqual(checked["stale_inputs"], [evidence["id"]])

    def test_historical_sqlite_schema_names_are_legacy_storage_only(self) -> None:
        TestamurVersionedStore(self.path)
        with TestamurStore(self.path).connect() as conn:
            tables = {str(row["name"]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for table in ("witness_projects","witness_objects","witness_revisions","witness_edges","witness_verification_runs","witness_revision_parents","witness_content_objects","witness_state_revisions","witness_state_revision_parents","witness_state_heads"):
            self.assertIn(table, tables)


if __name__ == "__main__":
    unittest.main()
