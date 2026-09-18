from __future__ import annotations

import unittest

from testamur.product_adapters import revision_pinned_impact_reader


class _RelianceView:
    def list(self, *, scope_ref: str, reliant_ref=None, object_ref=None):
        self.scope_ref = scope_ref
        return [
            {
                "receipt_id": "tst:reliance:fixture",
                "reliant_ref": "tst:record:downstream",
                "reliant_revision_ref": "tst:record-revision:downstream-v1",
                "object_ref": "tst:record:vendor-component",
                "purpose": "release.use",
                "policy_ids": ["tst:policy:release"],
                "pinned_revisions": {
                    "tst:record:vendor-component": "tst:revision:affected-v7"
                },
                "stale": False,
                "current_admissible": True,
                "created_at": "2026-09-17T00:00:00Z",
            }
        ]


class ProductRevisionImpactTest(unittest.TestCase):
    def test_exact_revision_pin_drives_review_obligation(self) -> None:
        store = _RelianceView()
        reader = revision_pinned_impact_reader(store, "tst:scope:release")
        result = reader("tst:revision:affected-v7")

        self.assertTrue(result["ok"])
        self.assertEqual(store.scope_ref, "tst:scope:release")
        self.assertEqual(
            result["impact"]["affected_reliant_refs"],
            ["tst:record:downstream"],
        )
        self.assertEqual(result["impact"]["affected_receipt_count"], 1)
        self.assertTrue(result["semantics"]["match_is_exact_pinned_revision"])
        self.assertTrue(result["semantics"]["review_obligation_only"])
        self.assertFalse(
            result["semantics"]["lineage_propagation_implies_vulnerability_verdict"]
        )
        self.assertFalse(result["semantics"]["affectedness_implies_downstream_false"])

    def test_object_identity_is_not_mistaken_for_revision_identity(self) -> None:
        reader = revision_pinned_impact_reader(_RelianceView(), "tst:scope:release")
        result = reader("tst:record:vendor-component")
        self.assertEqual(result["impact"]["affected_receipt_count"], 0)
        self.assertEqual(result["impact"]["affected_reliant_refs"], [])


if __name__ == "__main__":
    unittest.main()
