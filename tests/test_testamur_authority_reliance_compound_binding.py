from __future__ import annotations

from testamur.authority_reliance import authority_reliance_impact


class Receipts:
    def __init__(self, rows):
        self.rows = rows

    def list(self, *, scope_ref, reliant_ref=None, object_ref=None):
        return list(self.rows)


def action():
    return {
        "actionable_capabilities": [{
            "target_ref": "connector:github",
            "capability": {"namespace": "github", "action": "read", "resource": "repo:exact"},
            "path_edge_ids": ["edge:delegation"],
            "evidence_state": "recorded",
        }]
    }


def binding(**overrides):
    value = {
        "authority_target_ref": "connector:github",
        "binding_ref": "binding:exact-resource",
        "object_ref": "object:expected",
        "revision_ref": "revision:expected",
        "evidence": [{"ref": "evidence:binding", "evidence_class": "OBSERVED"}],
    }
    value.update(overrides)
    return value


def receipt(*, object_ref="object:expected", revision_ref="revision:expected"):
    return {
        "receipt_id": "receipt:1",
        "reliant_ref": "work:1",
        "object_ref": object_ref,
        "pinned_revisions": {"source": revision_ref},
    }


def test_compound_binding_requires_object_and_revision_to_match():
    result = authority_reliance_impact(
        action(),
        Receipts([receipt(object_ref="object:other")]),
        scope_ref="scope:1",
        bindings=[binding()],
    )
    assert result["impacts"] == []
    assert result["unmatched_actions"][0]["reason"] == "explicit_binding_did_not_match_any_durable_reliance"
    assert result["semantics"]["compound_bindings_are_conjunctive"] is True


def test_compound_binding_does_not_accept_object_only_match():
    result = authority_reliance_impact(
        action(),
        Receipts([receipt(revision_ref="revision:other")]),
        scope_ref="scope:1",
        bindings=[binding()],
    )
    assert result["impacts"] == []


def test_single_dimension_binding_still_matches_exact_recorded_dimension():
    result = authority_reliance_impact(
        action(),
        Receipts([receipt(revision_ref="revision:other")]),
        scope_ref="scope:1",
        bindings=[binding(revision_ref=None)],
    )
    assert result["impact_count"] == 1
    assert result["impacts"][0]["object_match"] is True
    assert result["impacts"][0]["revision_match"] is False
