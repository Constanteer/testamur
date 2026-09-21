from __future__ import annotations

from datetime import datetime

import pytest

from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_blast_engine import canonical_authority_blast_radius


def _store(tmp_path) -> TestamurAuthorityStore:
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    for ref in ("principal:a", "principal:b"):
        store.record_subject(
            AuthoritySubjectKind.PRINCIPAL,
            label=ref,
            subject_ref=ref,
        )
    store.record_subject(
        AuthoritySubjectKind.RESOURCE,
        label="resource:r",
        subject_ref="resource:r",
    )
    for seed in ("a", "b"):
        store.record_edge(
            f"principal:{seed}",
            AuthorityRelationType.CAN_READ,
            "resource:r",
            edge_id=f"edge:{seed}-read",
            capabilities=[{"namespace": "resource", "action": "read"}],
            evidence=[{"evidence_class": "OBSERVED", "ref": f"evidence:{seed}"}],
        )
    return store


def test_canonical_blast_keeps_seed_provenance_bound_to_exact_path(tmp_path):
    result = canonical_authority_blast_radius(
        _store(tmp_path),
        ["principal:b", "principal:a"],
        compromise_model="FULL_SUBJECT_COMPROMISE",
    )

    assert result["compromised_refs"] == ["principal:a", "principal:b"]
    actions = [item for item in result["actionable_capabilities"] if item["target_ref"] == "resource:r"]
    assert len(actions) == 2
    by_path = {tuple(item["path_edge_ids"]): item["compromise_seed_refs"] for item in actions}
    assert by_path[("edge:a-read",)] == ["principal:a"]
    assert by_path[("edge:b-read",)] == ["principal:b"]
    assert result["semantics"]["material_lineage_does_not_create_seed_provenance"] is True
    assert result["semantics"]["blast_results_are_bound_to_one_compromise_model"] is True
    assert result["semantics"]["blast_results_are_bound_to_requested_seed_traversals"] is True
    assert result["semantics"]["blast_results_require_authority_reachability_schema"] is True


def test_canonical_blast_uses_one_temporal_snapshot_for_all_seeds(tmp_path, monkeypatch):
    import testamur.authority_reachability_v2 as reachability

    observed_as_of = []
    original = reachability.authority_reachability

    def recording_reachability(*args, **kwargs):
        observed_as_of.append(kwargs.get("as_of"))
        return original(*args, **kwargs)

    monkeypatch.setattr(reachability, "authority_reachability", recording_reachability)
    result = canonical_authority_blast_radius(
        _store(tmp_path),
        ["principal:a", "principal:b"],
        compromise_model="FULL_SUBJECT_COMPROMISE",
    )

    assert len(observed_as_of) == 2
    assert observed_as_of[0] is observed_as_of[1]
    assert isinstance(observed_as_of[0], datetime)
    assert observed_as_of[0].tzinfo is not None
    assert result["as_of"] == observed_as_of[0].isoformat().replace("+00:00", "Z")
    assert result["semantics"]["blast_results_share_one_observation_instant"] is True


def test_canonical_blast_preserves_explicit_as_of_for_all_seeds(tmp_path, monkeypatch):
    import testamur.authority_reachability_v2 as reachability

    observed_as_of = []
    original = reachability.authority_reachability

    def recording_reachability(*args, **kwargs):
        observed_as_of.append(kwargs.get("as_of"))
        return original(*args, **kwargs)

    monkeypatch.setattr(reachability, "authority_reachability", recording_reachability)
    explicit = "2026-09-22T00:00:00Z"
    result = canonical_authority_blast_radius(
        _store(tmp_path),
        ["principal:a", "principal:b"],
        compromise_model="FULL_SUBJECT_COMPROMISE",
        as_of=explicit,
    )

    assert observed_as_of == [explicit, explicit]
    assert result["as_of"] == explicit


def test_canonical_blast_rejects_inconsistent_engine_observation_instants(tmp_path, monkeypatch):
    import testamur.authority_reachability_v2 as reachability

    original = reachability.authority_reachability
    calls = 0

    def inconsistent_reachability(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        result["as_of"] = f"2026-09-22T00:00:0{calls}Z"
        return result

    monkeypatch.setattr(reachability, "authority_reachability", inconsistent_reachability)
    with pytest.raises(ValueError, match="identical as_of"):
        canonical_authority_blast_radius(
            _store(tmp_path),
            ["principal:a", "principal:b"],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )


def test_canonical_blast_rejects_engine_result_from_another_compromise_model(tmp_path, monkeypatch):
    import testamur.authority_reachability_v2 as reachability

    original = reachability.authority_reachability
    calls = 0

    def inconsistent_model(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        if calls == 2:
            result["compromise_model"] = "READ_ONLY_COMPROMISE"
        return result

    monkeypatch.setattr(reachability, "authority_reachability", inconsistent_model)
    with pytest.raises(ValueError, match="requested compromise model"):
        canonical_authority_blast_radius(
            _store(tmp_path),
            ["principal:a", "principal:b"],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )


def test_canonical_blast_rejects_result_mislabeled_as_another_requested_seed(tmp_path, monkeypatch):
    import testamur.authority_reachability_v2 as reachability

    original = reachability.authority_reachability

    def mislabeled_seed(*args, **kwargs):
        result = original(*args, **kwargs)
        if result["starting_subject_ref"] == "principal:a":
            result["starting_subject_ref"] = "principal:b"
        return result

    monkeypatch.setattr(reachability, "authority_reachability", mislabeled_seed)
    with pytest.raises(ValueError, match="requested compromise seed"):
        canonical_authority_blast_radius(
            _store(tmp_path),
            ["principal:a", "principal:b"],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )


def test_canonical_blast_rejects_non_reachability_schema(tmp_path, monkeypatch):
    import testamur.authority_reachability_v2 as reachability

    original = reachability.authority_reachability

    def wrong_schema(*args, **kwargs):
        result = original(*args, **kwargs)
        result["schema_version"] = "testamur.authority-blast-radius.v1"
        return result

    monkeypatch.setattr(reachability, "authority_reachability", wrong_schema)
    with pytest.raises(ValueError, match="unsupported schema version"):
        canonical_authority_blast_radius(
            _store(tmp_path),
            ["principal:a"],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )


def test_canonical_blast_rejects_empty_seed_set(tmp_path):
    with pytest.raises(ValueError, match="compromised_refs"):
        canonical_authority_blast_radius(
            _store(tmp_path),
            [],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )