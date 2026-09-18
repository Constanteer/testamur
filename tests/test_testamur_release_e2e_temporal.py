from __future__ import annotations

from pathlib import Path

from testamur.temporal_model import (
    TemporalAssertion,
    TemporalBasis,
    TemporalMode,
    TemporalProjection,
)
from testamur.temporal_query import TemporalClause
from testamur.temporal_store import TemporalStore


def _observed(at: str) -> TemporalAssertion:
    return TemporalAssertion(at, basis=TemporalBasis.OBSERVED)


def test_gate_d_late_historical_evidence_does_not_leak_into_known_at(tmp_path: Path) -> None:
    store = TemporalStore(tmp_path / "testamur.sqlite3")
    projection = TemporalProjection(
        object_ref="tst:record:historical-source",
        recorded_at=_observed("2026-09-10T12:00:00Z"),
        published_at=TemporalAssertion(
            "2026-01-05T00:00:00Z",
            basis=TemporalBasis.ARCHIVE_OBSERVATION,
            source_ref="archive:snapshot:123",
        ),
    )
    store.append_projection(projection)

    known_then = store.query(
        [TemporalClause(TemporalMode.KNOWN_AT, "2026-02-01T00:00:00Z")],
        object_ref=projection.object_ref,
    )
    assert known_then == []

    available_then = store.query(
        [TemporalClause(TemporalMode.AVAILABLE_BY, "2026-02-01T00:00:00Z")],
        object_ref=projection.object_ref,
    )
    assert len(available_then) == 1
    assert available_then[0].recognized_retrospectively is True
    assert "available_by:publication_supported_by_cut" in available_then[0].reasons


def test_gate_d_available_by_fails_closed_without_publication_provenance(tmp_path: Path) -> None:
    store = TemporalStore(tmp_path / "testamur.sqlite3")
    projection = TemporalProjection(
        object_ref="tst:record:unproven-publication",
        recorded_at=_observed("2026-09-10T12:00:00Z"),
        published_at=TemporalAssertion(
            "2026-01-05T00:00:00Z",
            basis=TemporalBasis.UNKNOWN,
        ),
    )
    store.append_projection(projection)

    matches = store.query(
        [TemporalClause(TemporalMode.AVAILABLE_BY, "2026-02-01T00:00:00Z")],
        object_ref=projection.object_ref,
    )
    assert matches == []
