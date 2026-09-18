from __future__ import annotations

import unittest

import testamur.model as canonical
from testamur.contracts import ObjectKind as DurableObjectKind
from testamur.runtime_protocol import canonical_hash as runtime_canonical_hash


class TestamurModelNamespaceTest(unittest.TestCase):
    def test_public_semantic_model_is_owned_by_testamur(self) -> None:
        for value in (
            canonical.ObjectKind,
            canonical.EdgeKind,
            canonical.VerificationStatus,
            canonical.VerifierClass,
            canonical.canonical_json,
            canonical.canonical_hash,
        ):
            self.assertTrue(value.__module__.startswith("testamur"))

    def test_historical_schema_and_hash_wire_semantics_are_explicit(self) -> None:
        # Existing databases may still carry the historical schema token. It is
        # storage compatibility, not a second Python package/runtime.
        self.assertEqual(canonical.SCHEMA_VERSION, "witness-core-v0.1")
        value = {"z": [3, 2, 1], "a": {"unicode": "证据"}}
        self.assertEqual(
            canonical.canonical_json(value),
            '{"a":{"unicode":"证据"},"z":[3,2,1]}',
        )
        self.assertEqual(canonical.canonical_hash(value), runtime_canonical_hash(value))

    def test_semantic_and_durable_object_kind_namespaces_stay_distinct(self) -> None:
        self.assertIsNot(canonical.ObjectKind, DurableObjectKind)
        self.assertEqual(canonical.ObjectKind.EVIDENCE.value, "evidence")
        self.assertEqual(DurableObjectKind.RECORD.value, "record")

    def test_extensible_semantic_kind_validation_is_unchanged(self) -> None:
        self.assertEqual(canonical.normalize_object_kind("artifact"), "artifact")
        self.assertEqual(
            canonical.normalize_object_kind("engineering.measurement"),
            "engineering.measurement",
        )
        with self.assertRaisesRegex(ValueError, "Testamur semantic object kind"):
            canonical.normalize_object_kind("not namespaced")
        with self.assertRaisesRegex(ValueError, "Testamur semantic edge kind"):
            canonical.normalize_edge_kind("not namespaced")


if __name__ == "__main__":
    unittest.main()
