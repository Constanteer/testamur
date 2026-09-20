from __future__ import annotations

from testamur.authority import TestamurAuthorityStore
from testamur.authority_explain import explain_authority_path


def test_explanation_projects_path_support_and_boundaries_without_conflating_them(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    path_edge = store.record_edge(
        source_ref="principal:alice",
        target_ref="connector:github",
        relation_type="DELEGATES_TO",
        capabilities=[{"capability": "repo.read", "constraints": {"audience": "github", "scope": ["repo:acme/app"]}}],
        constraints={"audience": "github", "scope": ["repo:acme/app"]},
        boundary_refs=["boundary:github"],
        evidence=[{"evidence_class": "OBSERVED", "ref": "grant:1"}],
    )
    support_edge = store.record_edge(
        source_ref="credential:oauth-1",
        target_ref="principal:alice",
        relation_type="AUTHENTICATES_AS",
        capabilities=[],
        constraints={"audience": "github", "scope": ["repo:acme/app"]},
        evidence=[{"evidence_class": "OBSERVED", "ref": "token-introspection:1"}],
    )

    value = explain_authority_path(
        store,
        [path_edge["edge_id"]],
        supporting_edge_ids=[support_edge["edge_id"]],
    )

    assert value["authority_edges"] == value["transitions"]
    assert value["supporting_evidence"] == value["supporting_edges"]
    assert [edge["edge_id"] for edge in value["authority_edges"]] == [path_edge["edge_id"]]
    assert [edge["edge_id"] for edge in value["supporting_evidence"]] == [support_edge["edge_id"]]
    assert value["trust_boundary_crossings"] == [{
        "boundary_ref": "boundary:github",
        "edge_id": path_edge["edge_id"],
        "source_ref": "principal:alice",
        "target_ref": "connector:github",
        "path_index": 0,
    }]
    assert value["authority_edges"][0]["constraints"]["audience"] == "github"
    assert value["supporting_evidence"][0]["constraints"]["scope"] == ["repo:acme/app"]
    assert value["semantics"]["supporting_evidence_is_not_authority_path"] is True
    assert value["semantics"]["boundary_crossings_require_recorded_path_boundary_refs"] is True


def test_supporting_edge_boundary_is_not_projected_as_path_crossing(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    path_edge = store.record_edge(
        source_ref="principal:alice",
        target_ref="connector:github",
        relation_type="DELEGATES_TO",
        capabilities=[],
        evidence=[{"evidence_class": "OBSERVED", "ref": "grant:1"}],
    )
    support_edge = store.record_edge(
        source_ref="credential:oauth-1",
        target_ref="principal:alice",
        relation_type="AUTHENTICATES_AS",
        capabilities=[],
        boundary_refs=["boundary:idp"],
        evidence=[{"evidence_class": "OBSERVED", "ref": "token-introspection:1"}],
    )

    value = explain_authority_path(store, [path_edge["edge_id"]], supporting_edge_ids=[support_edge["edge_id"]])

    assert value["trust_boundary_crossings"] == []
    assert value["trust_boundary_refs"] == ["boundary:idp"]
