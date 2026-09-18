from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from testamur.product_service import TestamurProductService
from testamur.source_store import TestamurSourceStore


class ReleaseSourceHistoryCompareE2ETest(unittest.TestCase):
    def test_source_revision_history_compare_preserves_semantic_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "testamur.db"
            sources = TestamurSourceStore(database)
            source = sources.get_or_create_source("https://example.invalid/spec.txt")
            first = sources.record_snapshot(
                source["source_id"],
                content=b"version one\n",
                observed_at="2026-09-16T00:00:00Z",
                retrieval_metadata={"published_at": "2026-09-15T12:00:00Z"},
            )
            second = sources.record_snapshot(
                source["source_id"],
                content=b"version two\n",
                observed_at="2026-09-17T00:00:00Z",
                retrieval_metadata={"published_at": "2026-09-16T12:00:00Z"},
            )

            product = TestamurProductService(database)
            shown = product.get_object(source["source_id"])
            history = product.history(source["source_id"])
            compared = product.compare(first["snapshot_id"], second["snapshot_id"])

            self.assertTrue(shown["ok"])
            self.assertEqual(shown["data"]["source_id"], source["source_id"])
            self.assertTrue(history["ok"])
            self.assertEqual(len(history["items"]), 2)
            self.assertTrue(compared["ok"])
            comparison = compared["comparison"]
            self.assertTrue(comparison["content_changed"])
            self.assertTrue(comparison["semantics"]["mechanical_identity_comparison_only"])
            self.assertFalse(comparison["semantics"]["semantic_change_inferred"])

            # Local persistence time is not publication/effective time. The source
            # snapshot preserves caller provenance without promoting it into the
            # canonical temporal axes owned by W2.
            self.assertNotEqual(first["recorded_at"], first["observed_at"])
            self.assertEqual(
                first["retrieval_metadata"]["published_at"],
                "2026-09-15T12:00:00Z",
            )
            self.assertNotIn("effective_at", first)


if __name__ == "__main__":
    unittest.main()
