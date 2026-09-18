from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.versioned_store import (
    ASSURANCE_SNAPSHOT_VERSION,
    CONTENT_ADDRESS_VERSION,
    SNAPSHOT_VERSION,
    STATE_REVISION_VERSION,
    TestamurVersionedStore,
)


class TestamurVersionedStoreNamespaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "versioned.sqlite3"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_versioned_store_is_owned_by_testamur(self) -> None:
        self.assertTrue(TestamurVersionedStore.__module__.startswith("testamur."))

    def test_historical_wire_versions_are_preserved_as_legacy_storage_contracts(self) -> None:
        self.assertEqual(CONTENT_ADDRESS_VERSION, "witness-cas-v0.1")
        self.assertEqual(SNAPSHOT_VERSION, "witness-snapshot-v0.1")
        self.assertEqual(STATE_REVISION_VERSION, "witness-state-revision-v0.1")
        self.assertEqual(ASSURANCE_SNAPSHOT_VERSION, "witness-assurance-snapshot-v0.1")

    def test_snapshot_round_trip_reopens_through_testamur_only(self) -> None:
        canonical = TestamurVersionedStore(self.path)
        project = canonical.create_project("snapshot-ns", "Snapshot namespace")
        claim = canonical.create_object(project["id"], "claim", {"value": 1})
        canonical.revise_object(claim["id"], {"value": 2})
        snapshot = canonical.snapshot_project(
            project["id"],
            message="namespace fixture",
            actor_ref="testamur-test",
        )

        before = canonical.reconstruct_revision(snapshot["address"])
        integrity = canonical.verify_revision_integrity(snapshot["address"])
        self.assertTrue(integrity["ok"], integrity["errors"])

        reopened = TestamurVersionedStore(self.path)
        self.assertEqual(before, reopened.reconstruct_revision(snapshot["address"]))
        reopened_integrity = reopened.verify_revision_integrity(snapshot["address"])
        self.assertEqual(integrity, reopened_integrity)
        self.assertTrue(reopened_integrity["ok"], reopened_integrity["errors"])

    def test_later_revision_cannot_pollute_committed_snapshot(self) -> None:
        canonical = TestamurVersionedStore(self.path)
        project = canonical.create_project("immutability", "Immutability")
        claim = canonical.create_object(project["id"], "claim", {"value": 1})
        canonical.revise_object(claim["id"], {"value": 2})
        snapshot = canonical.snapshot_project(project["id"], message="before change")

        historical = canonical.reconstruct_revision(snapshot["address"])
        historical_claim = next(
            item for item in historical["objects"] if item["id"] == claim["id"]
        )
        self.assertEqual(historical_claim["payload"], {"value": 2})

        canonical.revise_object(claim["id"], {"value": 3})
        current = canonical.get_object(claim["id"])
        self.assertEqual(current["payload"], {"value": 3})

        reconstructed_again = TestamurVersionedStore(self.path).reconstruct_revision(snapshot["address"])
        self.assertEqual(historical, reconstructed_again)
        old_claim_again = next(
            item for item in reconstructed_again["objects"] if item["id"] == claim["id"]
        )
        self.assertEqual(old_claim_again["payload"], {"value": 2})


if __name__ == "__main__":
    unittest.main()
