import sqlite3

import pytest

from testamur.temporal_model import (
    TemporalAssertion,
    TemporalBasis,
    TemporalEvent,
    TemporalEventKind,
    TemporalPrecision,
    TemporalProjection,
)
from testamur.temporal_query import TemporalClause, known_at
from testamur.temporal_store import TemporalStore


def observed(value: str) -> TemporalAssertion:
    return TemporalAssertion(value, basis=TemporalBasis.OBSERVED)


def test_event_round_trip_preserves_occurrence_time_and_related_refs():
    event = TemporalEvent(
        TemporalEventKind.RETROSPECTIVE_DISCOVERY,
        "tst:snapshot:paper",
        observed("2028-01-20T00:00:00Z"),
        event_time=TemporalAssertion(
            "2023-04-01T00:00:00Z",
            basis=TemporalBasis.ARCHIVE_OBSERVATION,
            source_ref="archive:receipt:1",
        ),
        related_refs=("archive:receipt:1",),
        metadata={"note": "publication discovered later"},
    )
    restored = TemporalEvent.from_projection(event.to_projection())
    assert restored == event


def test_event_fuzzy_time_remains_fuzzy():
    event = TemporalEvent(
        "retrospective_discovery",
        "tst:record:r1",
        observed("2028-01-01T00:00:00Z"),
        event_time=TemporalAssertion.fuzzy(
            "circa 1910",
            precision=TemporalPrecision.CIRCA,
            basis=TemporalBasis.EXTERNALLY_DECLARED,
            source_ref="catalog:1",
        ),
    )
    restored = TemporalEvent.from_projection(event.to_projection())
    assert restored.event_time is not None
    assert restored.event_time.queryable is False
    assert restored.event_time.original_value == "circa 1910"


def test_event_metadata_cannot_override_reserved_semantics():
    with pytest.raises(ValueError, match="reserved"):
        TemporalEvent(
            "late_observation",
            "tst:snapshot:s",
            observed("2028-01-01T00:00:00Z"),
            metadata={"projection_kind": "not-an-event"},
        )


def test_event_rejects_string_related_refs_instead_of_splitting_characters():
    with pytest.raises(ValueError, match="sequence of refs"):
        TemporalEvent(
            "late_observation",
            "tst:snapshot:s",
            observed("2028-01-01T00:00:00Z"),
            related_refs="archive:receipt:1",  # type: ignore[arg-type]
        )


def test_event_rejects_invalid_event_time_type():
    with pytest.raises(ValueError, match="event_time must be a TemporalAssertion"):
        TemporalEvent(
            "late_observation",
            "tst:snapshot:s",
            observed("2028-01-01T00:00:00Z"),
            event_time="2020-01-01",  # type: ignore[arg-type]
        )


def test_event_rejects_nonmapping_metadata():
    with pytest.raises(ValueError, match="metadata must be a mapping"):
        TemporalEvent(
            "late_observation",
            "tst:snapshot:s",
            observed("2028-01-01T00:00:00Z"),
            metadata=[("x", 1)],  # type: ignore[arg-type]
        )


def test_append_event_is_idempotent_and_separate_from_normal_projection_views(tmp_path):
    store = TemporalStore(tmp_path / "temporal.sqlite")
    event = TemporalEvent(
        "historical_availability_established",
        "tst:snapshot:paper",
        observed("2028-01-20T00:00:00Z"),
        event_time=TemporalAssertion(
            "2023-04-01T00:00:00Z",
            basis=TemporalBasis.ARCHIVE_OBSERVATION,
            source_ref="archive:receipt:1",
        ),
    )
    first = store.append_event(event)
    second = store.append_event(event)
    assert first["event_id"] == second["event_id"]
    assert store.projections() == []
    assert len(store.projections(include_events=True)) == 1
    found = store.events_for("tst:snapshot:paper")
    assert [row["event_id"] for row in found] == [first["event_id"]]
    clause = [TemporalClause("known_at", "2029-01-01T00:00:00Z")]
    assert store.query(clause) == []
    assert len(store.query(clause, include_events=True)) == 1


def test_event_recorded_time_never_rewritten_by_historical_event_time(tmp_path):
    store = TemporalStore(tmp_path / "temporal.sqlite")
    store.append_event(
        TemporalEvent(
            "retrospective_discovery",
            "tst:snapshot:paper",
            observed("2028-01-20T00:00:00Z"),
            event_time=TemporalAssertion(
                "2023-04-01T00:00:00Z",
                basis=TemporalBasis.ARCHIVE_OBSERVATION,
                source_ref="archive:receipt:1",
            ),
        )
    )
    assert store.events_for(recorded_by="2024-12-31T23:59:59Z") == []
    assert len(store.events_for(recorded_by="2028-12-31T23:59:59Z")) == 1
    assert len(store.events_for(event_time_by="2024-12-31T23:59:59Z")) == 1


def test_event_time_filter_excludes_fuzzy_time_instead_of_guessing(tmp_path):
    store = TemporalStore(tmp_path / "temporal.sqlite")
    store.append_event(
        TemporalEvent(
            "retrospective_discovery",
            "tst:record:r",
            observed("2028-01-01T00:00:00Z"),
            event_time=TemporalAssertion.fuzzy(
                "circa 2020",
                precision=TemporalPrecision.CIRCA,
                basis=TemporalBasis.EXTERNALLY_DECLARED,
                source_ref="catalog:1",
            ),
        )
    )
    assert store.events_for(event_time_by="2021-01-01T00:00:00Z") == []
    assert len(store.events_for()) == 1


def test_in_memory_queries_fail_closed_on_mixed_perspectives():
    items = [
        TemporalProjection("x", observed("2025-01-01T10:00:00Z"), perspective="node:A"),
        TemporalProjection("x", observed("2025-01-01T12:00:00Z"), perspective="node:B"),
    ]
    with pytest.raises(ValueError, match="multiple perspectives"):
        known_at(items, "2025-01-02T00:00:00Z")
    result = known_at(items, "2025-01-02T00:00:00Z", perspective="node:A")
    assert len(result) == 1
    assert result[0].projection.perspective == "node:A"


def test_store_queries_fail_closed_on_mixed_perspectives_before_time_cut(tmp_path):
    store = TemporalStore(tmp_path / "temporal.sqlite")
    for perspective, at in [
        ("node:A", "2025-01-01T10:00:00Z"),
        ("node:B", "2025-01-01T12:00:00Z"),
    ]:
        store.append_projection(TemporalProjection("x", observed(at), perspective=perspective))
    clause = [TemporalClause("known_at", "2025-01-01T11:00:00Z")]
    with pytest.raises(ValueError, match="multiple perspectives"):
        store.query(clause, object_ref="x")
    assert len(store.query(clause, perspective="node:A", object_ref="x")) == 1


def test_store_object_scope_ignores_unrelated_other_perspective(tmp_path):
    store = TemporalStore(tmp_path / "temporal.sqlite")
    store.append_projection(
        TemporalProjection("x", observed("2025-01-01T10:00:00Z"), perspective="node:A")
    )
    store.append_projection(
        TemporalProjection("y", observed("2025-01-01T10:00:00Z"), perspective="node:B")
    )
    clause = [TemporalClause("known_at", "2025-01-02T00:00:00Z")]
    result = store.query(clause, object_ref="x")
    assert len(result) == 1
    assert result[0].projection.object_ref == "x"
    assert result[0].projection.perspective == "node:A"
    with pytest.raises(ValueError, match="object_ref"):
        store.query(clause, object_ref="   ")


def test_event_queries_fail_closed_on_mixed_perspectives(tmp_path):
    store = TemporalStore(tmp_path / "temporal.sqlite")
    for perspective in ["node:A", "node:B"]:
        store.append_event(
            TemporalEvent(
                "late_observation",
                "tst:snapshot:x",
                observed("2025-01-01T12:00:00Z"),
                perspective=perspective,
            )
        )
    with pytest.raises(ValueError, match="multiple perspectives"):
        store.events_for("tst:snapshot:x")
    assert len(store.events_for("tst:snapshot:x", perspective="node:A")) == 1


def test_event_subject_scope_ignores_unrelated_other_perspective(tmp_path):
    store = TemporalStore(tmp_path / "temporal.sqlite")
    store.append_event(
        TemporalEvent(
            "late_observation",
            "tst:snapshot:x",
            observed("2025-01-01T10:00:00Z"),
            perspective="node:A",
        )
    )
    store.append_event(
        TemporalEvent(
            "late_observation",
            "tst:snapshot:y",
            observed("2025-01-01T10:00:00Z"),
            perspective="node:B",
        )
    )
    result = store.events_for("tst:snapshot:x")
    assert len(result) == 1
    assert result[0]["event"]["perspective"] == "node:A"


def test_event_time_cut_cannot_silently_choose_perspective(tmp_path):
    store = TemporalStore(tmp_path / "temporal.sqlite")
    store.append_event(
        TemporalEvent(
            "late_observation",
            "tst:snapshot:x",
            observed("2025-01-01T10:00:00Z"),
            perspective="node:A",
        )
    )
    store.append_event(
        TemporalEvent(
            "late_observation",
            "tst:snapshot:x",
            observed("2025-01-01T12:00:00Z"),
            perspective="node:B",
        )
    )
    with pytest.raises(ValueError, match="multiple perspectives"):
        store.events_for(
            "tst:snapshot:x", recorded_by="2025-01-01T11:00:00Z"
        )


def test_event_kind_scope_and_single_string_kind_are_supported(tmp_path):
    store = TemporalStore(tmp_path / "temporal.sqlite")
    store.append_event(
        TemporalEvent(
            "late_observation",
            "tst:snapshot:x",
            observed("2025-01-01T10:00:00Z"),
            perspective="node:A",
        )
    )
    store.append_event(
        TemporalEvent(
            "retrospective_correction",
            "tst:snapshot:x",
            observed("2025-01-01T11:00:00Z"),
            perspective="node:B",
        )
    )
    late = store.events_for("tst:snapshot:x", event_kinds="late_observation")
    assert len(late) == 1
    assert late[0]["event"]["kind"] == "late_observation"
    corrections = store.events_for(
        "tst:snapshot:x", event_kinds=TemporalEventKind.RETROSPECTIVE_CORRECTION
    )
    assert len(corrections) == 1
    assert corrections[0]["event"]["perspective"] == "node:B"


def test_existing_pre_event_query_index_schema_migrates_without_mutating_assertions(tmp_path):
    path = tmp_path / "temporal.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE testamur_temporal_assertions(
      assertion_id TEXT PRIMARY KEY,
      object_ref TEXT NOT NULL,
      assertion_json TEXT NOT NULL,
      recorded_at TEXT NOT NULL
    );
    CREATE TABLE testamur_temporal_query_index(
      assertion_id TEXT PRIMARY KEY,
      object_ref TEXT NOT NULL,
      recorded_at TEXT NOT NULL,
      published_at TEXT,
      publication_supported INTEGER NOT NULL,
      valid_from TEXT,
      valid_until TEXT,
      has_effective INTEGER NOT NULL,
      perspective TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()
    TemporalStore(path)
    conn = sqlite3.connect(path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(testamur_temporal_query_index)")}
    conn.close()
    assert {"is_event", "event_kind", "event_time"}.issubset(columns)


def test_event_kind_filter_and_correction_history(tmp_path):
    store = TemporalStore(tmp_path / "temporal.sqlite")
    store.append_event(
        TemporalEvent(
            "retrospective_discovery",
            "tst:record-revision:A",
            observed("2026-01-01T00:00:00Z"),
            related_refs=("source:archive",),
        )
    )
    store.append_event(
        TemporalEvent(
            "retrospective_correction",
            "tst:record-revision:A",
            observed("2027-01-01T00:00:00Z"),
            related_refs=("tst:record-revision:B", "source:archive-2"),
        )
    )
    assert store.events_for(
        "tst:record-revision:A", recorded_by="2025-12-31T00:00:00Z"
    ) == []
    corrections = store.events_for(
        "tst:record-revision:A",
        event_kinds=[TemporalEventKind.RETROSPECTIVE_CORRECTION],
        recorded_by="2027-12-31T00:00:00Z",
    )
    assert len(corrections) == 1
    assert corrections[0]["event"]["related_refs"] == [
        "tst:record-revision:B",
        "source:archive-2",
    ]
