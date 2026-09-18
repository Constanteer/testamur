from __future__ import annotations

import unittest

from testamur.contracts import ObjectKind
from testamur.legacy_adapter import (
    ReferenceNamespace,
    WriteDisposition,
    resolve_reference,
)


class TestamurLegacyAdapterTest(unittest.TestCase):
    def test_testamur_ref_is_canonical_new_write(self) -> None:
        resolved = resolve_reference("tst:record:abc")
        self.assertEqual(resolved.namespace, ReferenceNamespace.TESTAMUR)
        self.assertEqual(resolved.write_disposition, WriteDisposition.CANONICAL_NEW_WRITE)
        self.assertEqual(resolved.durable_kind, ObjectKind.RECORD)
        self.assertTrue(resolved.canonical_for_new_writes)

    def test_historical_runtime_ref_remains_protocol_compatibility(self) -> None:
        resolved = resolve_reference("wtn:run:abc")
        self.assertEqual(resolved.namespace, ReferenceNamespace.HISTORICAL_WIRE)
        self.assertEqual(
            resolved.write_disposition,
            WriteDisposition.HISTORICAL_PROTOCOL_COMPATIBILITY,
        )
        self.assertEqual(resolved.durable_kind, ObjectKind.RUN)
        self.assertFalse(resolved.canonical_for_new_writes)

    def test_other_historical_wire_ids_are_not_silently_retyped(self) -> None:
        resolved = resolve_reference("wtn:artifact:deadbeef")
        self.assertEqual(resolved.namespace, ReferenceNamespace.HISTORICAL_WIRE)
        self.assertIsNone(resolved.durable_kind)

    def test_random_legacy_id_is_read_compatibility_only(self) -> None:
        resolved = resolve_reference("wrr_0123456789abcdef")
        self.assertEqual(resolved.namespace, ReferenceNamespace.LEGACY_RANDOM_ID)
        self.assertEqual(
            resolved.write_disposition,
            WriteDisposition.LEGACY_READ_COMPATIBILITY,
        )
        self.assertFalse(resolved.canonical_for_new_writes)

    def test_external_reference_stays_opaque(self) -> None:
        resolved = resolve_reference("sha256:abc")
        self.assertEqual(resolved.namespace, ReferenceNamespace.OPAQUE)
        self.assertEqual(
            resolved.write_disposition,
            WriteDisposition.OPAQUE_EXTERNAL_REFERENCE,
        )

    def test_empty_reference_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            resolve_reference("  ")


if __name__ == "__main__":
    unittest.main()
