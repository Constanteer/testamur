from __future__ import annotations

from datetime import datetime, timezone

import pytest

from testamur.authority import AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_reachability import CompromiseModel, authority_reachability


def _store(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    store.record_subject(AuthoritySubjectKind.WORKLOAD, label="worker", subject_ref="worker", attributes={})
    return store


def test_canonical_reachability_rejects_numeric_as_of_instead_of_stringifying(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="as_of"):
        authority_reachability(
            store,
            "worker",
            compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION,
            as_of=123,
        )


def test_canonical_reachability_rejects_naive_datetime_instead_of_assuming_utc(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="timezone"):
        authority_reachability(
            store,
            "worker",
            compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION,
            as_of=datetime(2026, 9, 23, 12, 0, 0),
        )


def test_canonical_reachability_rejects_naive_iso_timestamp(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="timezone"):
        authority_reachability(
            store,
            "worker",
            compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION,
            as_of="2026-09-23T12:00:00",
        )


def test_canonical_reachability_accepts_explicit_timezone_and_projects_semantics(tmp_path):
    store = _store(tmp_path)
    result = authority_reachability(
        store,
        "worker",
        compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION,
        as_of=datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result["as_of"] == "2026-09-23T12:00:00Z"
    assert result["semantics"]["as_of_requires_explicit_timezone_when_supplied"] is True
    assert result["semantics"]["compromise_model_requires_exact_identity"] is True


def test_canonical_reachability_rejects_typed_compromise_model_identity(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="compromise_model"):
        authority_reachability(store, "worker", compromise_model={"model": "PROCESS_CODE_EXECUTION"})
