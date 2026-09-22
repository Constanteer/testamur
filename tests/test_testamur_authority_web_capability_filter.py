from __future__ import annotations

import pytest

from testamur.authority_web_service import authority_blast_web, authority_reach_web


class _Service:
    def __init__(self) -> None:
        self.calls = []

    def authority_reach(self, ref, **options):
        self.calls.append(("reach", ref, options))
        return {"authority": {"reachable_subjects": [], "actionable_capabilities": [], "blocked_transitions": [], "trust_boundary_refs": [], "trust_boundary_crossings": [], "semantics": {}}}

    def authority_blast(self, refs, **options):
        self.calls.append(("blast", refs, options))
        return {"authority": {"reachable_subjects": [], "actionable_capabilities": [], "blocked_transitions": [], "trust_boundary_refs": [], "trust_boundary_crossings": [], "semantics": {}}}


def test_reach_web_forwards_filter_through_product_normalization():
    service = _Service()
    authority_reach_web(
        service,
        "subject:a",
        compromise_model="FULL_SUBJECT_COMPROMISE",
        capability_filter=[(" github ", " contents:write ")],
    )
    assert service.calls[0][2]["capability_filter"] == [("github", "contents:write")]


def test_blast_web_preserves_explicit_empty_filter_not_wildcard():
    service = _Service()
    authority_blast_web(
        service,
        ["subject:a"],
        compromise_model="FULL_SUBJECT_COMPROMISE",
        capability_filter=[],
    )
    assert service.calls[0][2]["capability_filter"] == []


def test_web_filter_does_not_bypass_product_fail_closed_validation():
    service = _Service()
    with pytest.raises(ValueError):
        authority_reach_web(
            service,
            "subject:a",
            compromise_model="FULL_SUBJECT_COMPROMISE",
            capability_filter=[("github", "")],
        )
    assert service.calls == []
