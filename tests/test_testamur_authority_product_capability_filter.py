from __future__ import annotations

import pytest

from testamur.authority_product_service import authority_blast_product, authority_reach_product


class _Service:
    def __init__(self) -> None:
        self.calls = []

    def authority_reach(self, ref, **options):
        self.calls.append(("reach", ref, options))
        return {"authority": {"reachable_subjects": [], "actionable_capabilities": [], "blocked_transitions": [], "trust_boundary_refs": [], "trust_boundary_crossings": [], "semantics": {}}}

    def authority_blast(self, refs, **options):
        self.calls.append(("blast", refs, options))
        return {"authority": {"reachable_subjects": [], "actionable_capabilities": [], "blocked_transitions": [], "trust_boundary_refs": [], "trust_boundary_crossings": [], "semantics": {}}}


def test_reach_product_passes_only_explicit_normalized_capability_filter():
    service = _Service()
    authority_reach_product(service, "subject:a", compromise_model="FULL_SUBJECT_COMPROMISE", capability_filter=[(" github ", " contents:write ")])
    assert service.calls[0][2]["capability_filter"] == [("github", "contents:write")]


def test_blast_product_preserves_empty_filter_as_empty_not_wildcard():
    service = _Service()
    authority_blast_product(service, ["subject:a"], compromise_model="FULL_SUBJECT_COMPROMISE", capability_filter=[])
    assert service.calls[0][2]["capability_filter"] == []


@pytest.mark.parametrize("bad", [[("github", "")], [("", "read")], [("github", 7)], [{"namespace": "github", "action": "read"}]])
def test_product_capability_filter_rejects_malformed_or_implicit_evidence(bad):
    service = _Service()
    with pytest.raises(ValueError):
        authority_reach_product(service, "subject:a", compromise_model="FULL_SUBJECT_COMPROMISE", capability_filter=bad)
    assert service.calls == []
