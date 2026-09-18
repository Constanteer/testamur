from __future__ import annotations

import sqlite3

import pytest

from testamur.agent_capture import AgentCapture
from testamur.work_session import (
    UsageState,
    WorkSessionStatus,
    WorkSessionStore,
)


def new_store(tmp_path) -> WorkSessionStore:
    return WorkSessionStore(tmp_path / "work.db")


def test_lifecycle_is_explicit_and_ordered(tmp_path):
    store = new_store(tmp_path)
    session = store.start_session(
        initiating_actor_ref="human:hank",
        host_environment="codex",
        project_ref="project:test",
    )
    assert session.status is WorkSessionStatus.OPEN
    with pytest.raises(ValueError):
        store.mark_pushed(session.session_id, push_ref="push:1")

    completed = store.complete(session.session_id)
    assert completed.status is WorkSessionStatus.COMPLETED_UNRECONCILED
    assert completed.ended_at is not None
    with pytest.raises(ValueError):
        store.abort(session.session_id)


def test_exposure_requires_prior_exact_revision_and_never_promotes_reliance(tmp_path):
    store = new_store(tmp_path)
    session = store.start_session(
        initiating_actor_ref="human:hank",
        host_environment="codex",
    )
    capture = AgentCapture(store)
    candidate = capture.discover(session.session_id, locator="https://example.test/spec")

    with pytest.raises(ValueError):
        capture.expose_to_model(
            session.session_id,
            candidate.candidate_id,
            source_revision_id="tst:revision:r1",
            generation_or_step_id="step:1",
            evidence_refs=("region:1",),
        )

    capture.fetched(
        session.session_id,
        candidate.candidate_id,
        source_revision_id="tst:revision:r1",
        retrieval_receipt_ref="receipt:1",
    )
    capture.expose_to_model(
        session.session_id,
        candidate.candidate_id,
        source_revision_id="tst:revision:r1",
        generation_or_step_id="step:1",
        evidence_refs=("region:1",),
    )
    states = [o.usage_state for o in store.observations(session.session_id)]
    assert states == [UsageState.DISCOVERED, UsageState.FETCHED, UsageState.EXPOSED_TO_MODEL]
    assert UsageState.RELIED_ON_BY_PROJECT_OBJECT not in states


def test_records_are_append_only_at_database_boundary(tmp_path):
    store = new_store(tmp_path)
    session = store.start_session(
        initiating_actor_ref="human:hank",
        host_environment="codex",
    )
    with pytest.raises(sqlite3.DatabaseError):
        store._conn.execute(
            "UPDATE testamur_work_sessions SET payload_json=payload_json WHERE session_id=?",
            (session.session_id,),
        )


def test_rediscovery_reuses_candidate_but_preserves_distinct_observation(tmp_path):
    store = new_store(tmp_path)
    session = store.start_session(
        initiating_actor_ref="human:hank",
        host_environment="codex",
        started_at="2026-09-16T15:00:00Z",
    )
    capture = AgentCapture(store)
    first = capture.discover(
        session.session_id,
        locator="https://example.test/spec",
        title="Spec v1 title",
        metadata={"rank": 1},
        observed_at="2026-09-16T15:01:00Z",
    )
    second = capture.discover(
        session.session_id,
        locator="https://example.test/spec",
        title="Spec title changed",
        metadata={"rank": 3},
        observed_at="2026-09-16T15:05:00Z",
    )
    assert first.candidate_id == second.candidate_id
    assert len(store.list_candidates(session.session_id)) == 1
    discovered = [
        o for o in store.observations(session.session_id)
        if o.usage_state is UsageState.DISCOVERED
    ]
    assert len(discovered) == 2
    assert discovered[0].metadata["title"] == "Spec v1 title"
    assert discovered[1].metadata["title"] == "Spec title changed"
