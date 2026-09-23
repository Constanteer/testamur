from __future__ import annotations

import pytest

from testamur.authority_exact_store import ExactAuthorityStoreView


class _Store:
    def __init__(self, edge, subject=None):
        self.edge = edge
        self.subject = subject

    def edges_from(self, source_ref):
        return [self.edge]

    def list_edges(self, *args, **kwargs):
        return [self.edge]

    def get_edge(self, edge_id):
        return self.edge

    def maybe_subject(self, subject_ref):
        return self.subject

    def get_subject(self, subject_ref):
        return self.subject


def _edge(**overrides):
    value = {
        "edge_id": "edge:1",
        "source_ref": "connector:one",
        "target_ref": "service:github",
        "relation_type": "DELEGATES",
        "constraints": {"service_ref": "service:github"},
    }
    value.update(overrides)
    return value


def test_exact_store_preserves_valid_authority_edge():
    view = ExactAuthorityStoreView(_Store(_edge()))
    assert view.edges_from("connector:one")[0]["target_ref"] == "service:github"


@pytest.mark.parametrize(
    "field,value",
    [
        ("edge_id", 1),
        ("source_ref", {"ref": "connector:one"}),
        ("target_ref", 7),
        ("relation_type", ["DELEGATES"]),
    ],
)
def test_exact_store_rejects_typed_edge_identity(field, value):
    view = ExactAuthorityStoreView(_Store(_edge(**{field: value})))
    with pytest.raises(ValueError):
        view.edges_from("connector:one")


def test_exact_store_rejects_connectivity_shaped_service_binding():
    edge = _edge(constraints={"service_ref": {"target_ref": "service:github", "connected": True}})
    view = ExactAuthorityStoreView(_Store(edge))
    with pytest.raises(ValueError):
        view.edges_from("connector:one")


def test_exact_store_rejects_malformed_acceptance_candidate_before_lookup_result_is_used():
    edge = _edge(edge_id=99, relation_type="ACCEPTS_CREDENTIAL")
    view = ExactAuthorityStoreView(_Store(edge))
    with pytest.raises(ValueError):
        view.list_edges(source_ref="service:github", target_ref="credential:one")


def test_exact_store_rejects_typed_subject_kind_before_credential_classification():
    subject = {"subject_ref": "credential:one", "kind": {"value": "TOKEN"}, "attributes": {}}
    view = ExactAuthorityStoreView(_Store(_edge(), subject=subject))
    with pytest.raises(ValueError):
        view.maybe_subject("credential:one")


def test_exact_store_rejects_non_mapping_subject_attributes():
    subject = {"subject_ref": "credential:one", "kind": "TOKEN", "attributes": ["scope:repo"]}
    view = ExactAuthorityStoreView(_Store(_edge(), subject=subject))
    with pytest.raises(ValueError):
        view.maybe_subject("credential:one")


def test_exact_store_rejects_typed_declared_evidence_class_before_projection():
    edge = _edge(evidence=[{"evidence_class": {"name": "DECLARED"}}])
    view = ExactAuthorityStoreView(_Store(edge))
    with pytest.raises(ValueError):
        view.edges_from("connector:one")


def test_exact_store_rejects_scalar_evidence_container():
    view = ExactAuthorityStoreView(_Store(_edge(evidence="DECLARED")))
    with pytest.raises(ValueError):
        view.edges_from("connector:one")


def test_exact_store_rejects_typed_lookup_refs_before_connectivity_can_be_queried():
    view = ExactAuthorityStoreView(_Store(_edge()))
    with pytest.raises(ValueError):
        view.list_edges(source_ref={"ref": "service:github"}, target_ref="credential:one")
