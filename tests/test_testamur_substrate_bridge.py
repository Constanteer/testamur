from __future__ import annotations

import unittest

from testamur.contracts import ObjectKind
from testamur.substrate_bridge import (
    BRIDGE_IDENTITY_VERSION,
    BridgeConflictError,
    ProjectionRelation,
    compare_legacy_projections,
    legacy_extension_ref,
    legacy_identity,
    project_legacy_object,
    reconcile_legacy_projection,
)


class TestamurSubstrateBridgeTest(unittest.TestCase):
    def test_identity_is_stable_across_domain_workers(self) -> None:
        identity = legacy_identity("wrr_0123456789abcdef")
        self.assertEqual(identity["identity_version"], BRIDGE_IDENTITY_VERSION)
        self.assertEqual(identity["source_namespace"], "witness")
        self.assertEqual(identity["source_ref"], "wrr_0123456789abcdef")
        first = legacy_extension_ref(ObjectKind.RELIANCE, "wrr_0123456789abcdef")
        second = legacy_extension_ref("reliance", "wrr_0123456789abcdef")
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("tst:reliance:"))

    def test_source_namespace_participates_in_identity(self) -> None:
        witness_ref = legacy_extension_ref(ObjectKind.POLICY, "policy:1", source_namespace="witness")
        imported_ref = legacy_extension_ref(ObjectKind.POLICY, "policy:1", source_namespace="external")
        self.assertNotEqual(witness_ref, imported_ref)

    def test_projection_preserves_provenance_without_semantic_promotion(self) -> None:
        envelope = project_legacy_object(
            ObjectKind.ASSESSMENT,
            source_ref="assessment:legacy",
            payload={"state": "UNKNOWN"},
            provenance={"database": "legacy.sqlite3", "rowid": 7},
            source_schema="legacy-assessment-v1",
        )
        item = envelope.to_json()
        self.assertEqual(
            item["canonical_ref"],
            legacy_extension_ref(ObjectKind.ASSESSMENT, "assessment:legacy"),
        )
        self.assertEqual(item["payload"], {"state": "UNKNOWN"})
        self.assertEqual(item["provenance"]["rowid"], 7)
        self.assertFalse(item["semantic_guarantees"]["verification_promoted"])
        self.assertFalse(item["semantic_guarantees"]["truth_promoted"])
        self.assertFalse(item["semantic_guarantees"]["authority_promoted"])

    def test_facade_makes_revision_vs_idempotence_explicit(self) -> None:
        first = project_legacy_object(
            ObjectKind.WORK_SESSION,
            source_ref="session:1",
            payload={"state": "OPEN"},
            provenance={"revision": 1},
        )
        second = project_legacy_object(
            ObjectKind.WORK_SESSION,
            source_ref="session:1",
            payload={"state": "RECONCILED"},
            provenance={"revision": 2},
        )
        comparison = compare_legacy_projections(first, second)
        self.assertEqual(comparison.relation, ProjectionRelation.SAME_IDENTITY_CHANGED)
        with self.assertRaises(BridgeConflictError):
            reconcile_legacy_projection(first, second)
        self.assertIs(
            reconcile_legacy_projection(first, second, allow_explicit_revision=True),
            second,
        )

    def test_core_store_kind_cannot_be_projected_as_extension(self) -> None:
        with self.assertRaises(ValueError):
            legacy_extension_ref(ObjectKind.RECORD, "legacy-record")


if __name__ == "__main__":
    unittest.main()
