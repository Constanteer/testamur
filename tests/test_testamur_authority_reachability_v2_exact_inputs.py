from __future__ import annotations

from datetime import datetime

import pytest

from testamur.authority_reachability_v2 import (
    CompromiseModel,
    authority_blast_radius,
    authority_reachability,
)


class _Store:
    def __init__(self, edges=None, subjects=None):
        self.edges = list(edges or [])
        self.subjects = dict(subjects or {})

    def edges_from(self, source_ref):
        return [edge for edge in self.edges if edge.get("source_ref") == source_ref]

    def list_edges(self, *, source_ref=None, target_ref=None, relation_type=None, **_kwargs):
        result = self.edges
        if source_ref is not None:
            result = [edge for edge in result if edge.get("source_ref") == source_ref]
        if target_ref is not None:
            result = [edge for edge in result if edge.get("target_ref") == target_ref]
        if relation_type is not None:
            expected = getattr(relation_type, "value", relation_type)
            result = [edge for edge in result if edge.get("relation_type") == expected]
        return result

    def get_edge(self, edge_id):
        for edge in self.edges:
            if edge.get("edge_id") == edge_id:
                return edge
        raise KeyError(edge_id)

    def maybe_subject(self, subject_ref):
        return self.subjects.get(subject_ref)


def test_raw_reachability_rejects_typed_starting_subject():
    with pytest.raises(ValueError):
        authority_reachability(_Store(), {"ref": "actor:one"}, compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE)


def test_raw_blast_radius_rejects_affectedness_shaped_seed():
    with pytest.raises(ValueError):
        authority_blast_radius(_Store(), [{"subject_ref": "actor:one", "affected": True}], compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE)


@pytest.mark.parametrize("as_of", [datetime(2026, 9, 24, 2, 0), "2026-09-24T02:00:00", 123])
def test_raw_reachability_requires_explicit_timezone(as_of):
    with pytest.raises(ValueError):
        authority_reachability(_Store(), "actor:one", compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE, as_of=as_of)


def test_raw_reachability_rejects_typed_compromise_model():
    with pytest.raises(ValueError):
        authority_reachability(_Store(), "actor:one", compromise_model={"name": "FULL_SUBJECT_COMPROMISE"})


def test_raw_reachability_rejects_typed_edge_identity_before_traversal():
    edge = {
        "edge_id": 7,
        "source_ref": "actor:one",
        "target_ref": "service:github",
        "relation_type": "CAN_READ",
    }
    with pytest.raises(ValueError):
        authority_reachability(_Store(edges=[edge]), "actor:one", compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE)


def test_raw_reachability_rejects_connectivity_shaped_service_binding():
    edge = {
        "edge_id": "edge:auth",
        "source_ref": "credential:one",
        "target_ref": "account:one",
        "relation_type": "CAN_AUTHENTICATE_AS",
        "constraints": {"service_ref": {"ref": "service:github", "connected": True}},
    }
    with pytest.raises(ValueError):
        authority_reachability(_Store(edges=[edge]), "credential:one", compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE)


def test_raw_reachability_keeps_connectivity_separate_from_authority():
    edge = {
        "edge_id": "edge:connect",
        "source_ref": "actor:one",
        "target_ref": "service:github",
        "relation_type": "CAN_CONNECT",
    }
    result = authority_reachability(_Store(edges=[edge]), "actor:one", compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE)
    assert result["actionable_capabilities"] == []
    assert [item["subject_ref"] for item in result["reachable_subjects"]] == ["actor:one"]
    assert result["semantics"]["network_reachability_does_not_mean_authorization"] is True
