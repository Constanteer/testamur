from __future__ import annotations

import pytest

from testamur.authority_reliance import authority_reliance_impact


class _RelianceStore:
    def list(self, *, scope_ref: str, reliant_ref=None, object_ref=None):
        assert scope_ref == "scope:demo"
        return [{
            "receipt_id": "receipt:1",
            "reliant_ref": "artifact:consumer",
            "reliant_revision_ref": "rev:consumer",
            "object_ref": "resource:repo",
            "pinned_revisions": {"source": "rev:repo"},
        }]


_BINDINGS = [{
    "authority_target_ref": "resource:repo",
    "binding_ref": "binding:repo",
    "object_ref": "resource:repo",
    "revision_ref": "rev:repo",
    "evidence": [{"ref": "evidence:binding", "evidence_class": "OBSERVED"}],
}]


def _result(action):
    return {"actionable_capabilities": [action], "compromised_refs": ["principal:a", "principal:b"]}


def _action(**extra):
    value = {
        "target_ref": "resource:repo",
        "capability": {"namespace": "github", "action": "contents:write", "resource": "repo"},
        "path_edge_ids": ["edge:a", "edge:repo"],
        "evidence_state": "CORROBORATED",
    }
    value.update(extra)
    return value


def test_reliance_impact_preserves_exact_recorded_compromise_seed_refs():
    projected = authority_reliance_impact(
        _result(_action(compromise_seed_refs=["principal:b", "principal:a", "principal:a"])),
        _RelianceStore(),
        scope_ref="scope:demo",
        bindings=_BINDINGS,
    )

    assert projected["impacts"][0]["compromise_seed_refs"] == ["principal:a", "principal:b"]
    assert projected["semantics"]["compromise_seed_provenance_is_engine_recorded_not_reliance_inferred"] is True


def test_missing_action_seed_provenance_is_not_inferred_from_global_compromised_refs():
    projected = authority_reliance_impact(
        _result(_action()),
        _RelianceStore(),
        scope_ref="scope:demo",
        bindings=_BINDINGS,
    )

    assert projected["impacts"][0]["compromise_seed_refs"] == []


def test_unmatched_action_preserves_recorded_seed_provenance():
    projected = authority_reliance_impact(
        _result(_action(target_ref="resource:unbound", compromise_seed_refs=["principal:a"])),
        _RelianceStore(),
        scope_ref="scope:demo",
        bindings=_BINDINGS,
    )

    assert projected["unmatched_actions"][0]["compromise_seed_refs"] == ["principal:a"]


def test_malformed_action_seed_provenance_fails_closed():
    with pytest.raises(ValueError, match="compromise_seed_refs"):
        authority_reliance_impact(
            _result(_action(compromise_seed_refs="principal:a")),
            _RelianceStore(),
            scope_ref="scope:demo",
            bindings=_BINDINGS,
        )
