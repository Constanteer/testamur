from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.blob_store import BlobIntegrityError, TestamurBlobStore
from testamur.mechanical_diff import compare_blobs


class TestamurBlobDiffTest(unittest.TestCase):
    def test_content_addressed_put_is_idempotent_and_rights_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurBlobStore(Path(raw) / "blobs")
            first = store.put(b"hello\n")
            second = store.put(b"hello\n")
            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(first["content_hash"], second["content_hash"])
            self.assertEqual(store.get(first["content_hash"]), b"hello\n")
            described = store.describe(first["content_hash"])
            self.assertTrue(described["integrity_verified"])
            self.assertFalse(described["publication_rights_implied"])

    def test_corrupted_blob_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurBlobStore(Path(raw) / "blobs")
            stored = store.put(b"original")
            path = store._path(stored["content_hash"])
            path.write_bytes(b"tampered")
            self.assertFalse(store.has(stored["content_hash"], verify=True))
            with self.assertRaises(BlobIntegrityError):
                store.get(stored["content_hash"])
            with self.assertRaises(BlobIntegrityError):
                store.put(b"original")

    def test_text_diff_is_deterministic_mechanical_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurBlobStore(Path(raw) / "blobs")
            left = store.put(b"alpha\nbeta\n")
            right = store.put(b"alpha\ngamma\nextra\n")
            value = compare_blobs(
                store,
                left["content_hash"],
                right["content_hash"],
            )
            self.assertEqual(value["kind"], "text")
            self.assertFalse(value["same_exact_content"])
            self.assertEqual(value["additions"], 2)
            self.assertEqual(value["deletions"], 1)
            self.assertIn("-beta", value["diff"])
            self.assertIn("+gamma", value["diff"])
            self.assertFalse(value["semantics"]["semantic_change_inferred"])
            self.assertFalse(value["semantics"]["publication_rights_implied"])

    def test_identical_hash_short_circuits_diff(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurBlobStore(Path(raw) / "blobs")
            ref = store.put(b"same")
            value = compare_blobs(store, ref["content_hash"], ref["content_hash"])
            self.assertEqual(value["kind"], "identical")
            self.assertEqual(value["diff"], "")
            self.assertEqual(value["additions"], 0)
            self.assertEqual(value["deletions"], 0)

    def test_binary_data_falls_back_to_exact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurBlobStore(Path(raw) / "blobs")
            left = store.put(bytes([0xFF, 0x00, 0x01]))
            right = store.put(bytes([0xFE, 0x00, 0x01]))
            value = compare_blobs(store, left["content_hash"], right["content_hash"])
            self.assertEqual(value["kind"], "binary")
            self.assertIsNone(value["diff"])
            self.assertFalse(value["same_exact_content"])

    def test_inline_diff_respects_byte_budget(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurBlobStore(Path(raw) / "blobs")
            left = store.put(b"a" * 20)
            right = store.put(b"b" * 20)
            value = compare_blobs(
                store,
                left["content_hash"],
                right["content_hash"],
                max_bytes=10,
            )
            self.assertEqual(value["kind"], "too_large_for_inline_diff")
            self.assertIsNone(value["diff"])
            self.assertEqual(value["max_bytes"], 10)

    def test_get_rejects_requested_size_budget_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = TestamurBlobStore(Path(raw) / "blobs")
            ref = store.put(b"123456")
            with self.assertRaises(ValueError):
                store.get(ref["content_hash"], max_bytes=5)


if __name__ == "__main__":
    unittest.main()
