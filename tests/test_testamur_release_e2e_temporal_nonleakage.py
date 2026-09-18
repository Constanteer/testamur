from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.temporal_model import TemporalAssertion, TemporalBasis, TemporalProjection
from testamur.temporal_query import TemporalClause
from testamur.temporal_store import TemporalStore


class ReleaseTemporalNonLeakageE2ETest(unittest.TestCase):
    def test_late_historical_evidence_does_not_leak_into_known_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TemporalStore(Path(tmp) / "testamur.sqlite3")
            ref = "tst:record-revision:historical-fixture"
            store.append_projection(
                TemporalProjection(
                    object_ref=ref,
                    # Testamur first learned this evidence in 2028.
                    recorded_at=TemporalAssertion(
                        "2028-06-01T00:00:00Z", basis=TemporalBasis.OBSERVED
                    ),
                    # The evidence says it was publicly available in 2023 and
                    # carries explicit source provenance for that assertion.
                    published_at=TemporalAssertion(
                        "2023-03-01T00:00:00Z",
                        basis=TemporalBasis.SOURCE_METADATA,
                        source_ref="tst:source:publication-fixture",
                    ),
                )
            )

            known_2024 = store.query(
                [TemporalClause(mode="known_at", at="2024-01-01T00:00:00Z")]
            )
            available_2024 = store.query(
                [TemporalClause(mode="available_by", at="2024-01-01T00:00:00Z")]
            )
            known_2029 = store.query(
                [TemporalClause(mode="known_at", at="2029-01-01T00:00:00Z")]
            )

            self.assertEqual(known_2024, [])
            self.assertEqual([item.projection.object_ref for item in available_2024], [ref])
            self.assertEqual([item.projection.object_ref for item in known_2029], [ref])

    def test_available_by_requires_publication_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TemporalStore(Path(tmp) / "testamur.sqlite3")
            ref = "tst:record-revision:no-publication-provenance"
            store.append_projection(
                TemporalProjection(
                    object_ref=ref,
                    recorded_at=TemporalAssertion(
                        "2028-06-01T00:00:00Z", basis=TemporalBasis.OBSERVED
                    ),
                    # OBSERVED is valid as a temporal assertion, but does not
                    # establish external publication/availability provenance.
                    published_at=TemporalAssertion(
                        "2023-03-01T00:00:00Z", basis=TemporalBasis.OBSERVED
                    ),
                )
            )

            available = store.query(
                [TemporalClause(mode="available_by", at="2024-01-01T00:00:00Z")]
            )
            self.assertEqual(available, [])


if __name__ == "__main__":
    unittest.main()
