from __future__ import annotations

from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_explain import explain_authority_path


OBSERVED = [{"evidence_class": "OBSERVED", "ref": "evidence:observed"}]


def _subject(store, ref, kind):
    store.record_subject(kind, label=ref, subject_ref=ref, attributes={})


def _fixture(store):
    _subject(store, "principal:alice", AuthoritySubjectKind.PRINCIPAL)
    _subject(store, "connector:github", AuthoritySubjectKind.CONNECTOR)
    _subject(store, "credential:oauth-1", AuthoritySubjectKind.CREDENTIAL)
    path_edge = store.record_edge(
        "principal:alice",
        AuthorityRelationType.DELEGATES,
        "connector:github",
        capabilities=[{"namespace": "github", "action": "contents.read", "resource": "repo:acme/app", "constraints": {"required_audiences": ["github"], "required_scopes": ["repo:read"]}}],
        constraints={"required_audiences": ["github"], "required_scopes": ["repo:read"]},
        boundary_refs=["boundary:github"],
        evidence=OBSERVED,
    )
    support_edge = store.record_edge(
        "credential:oauth-1",
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        "principal:alice",
        constraints={"required_audiences": ["github"], "required_scopes": ["repo:read"]},
        evidence=[{"evidence_class": "OBSERVED", "ref": "token-introspection:1"}],
    )
    return path_edge, support_edge


def test_explanation_projects_path_support_and_boundaries_without_conflating_them(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    path_edge, support_edge = _fixture(store)
    value = explain_authority_path(store, [path_edge["edge_id"]], supporting_edge_ids=[support_edge["edge_id"]])

    assert value["authority_edges"] == value["transitions"]
    assert value["supporting_evidence"] == value["supporting_edges"]
    assert [edge["edge_id"] for edge in value["authority_edges"]] == [path_edge["edge_id"]]
    assert [edge["edge_id"] for edge in value["supporting_evidence"]] == [support_edge["edge_id"]]
    assert value["trust_boundary_crossings"] == [{"boundary_ref": "boundary:github", "edge_id": path_edge["edge_id"], "source_ref": "principal:alice", "target_ref": "connector:github", "path_index": 0}]
    assert value["authority_edges"][0]["constraints"]["required_audiences"] == ["github"]
    assert value["supporting_evidence"][0]["constraints"]["required_scopes"] == ["repo:read"]
    assert value["authority_edges"][0]["recorded_constraint_semantics"] == {"audiences": ["github"], "scopes": ["repo:read"]}
    assert value["supporting_evidence"][0]["recorded_constraint_semantics"] == {"audiences": ["github"], "scopes": ["repo:read"]}
    assert value["semantics"]["supporting_evidence_is_not_authority_path"] is True
    assert value["semantics"]["boundary_crossings_require_recorded_path_boundary_refs"] is True
    assert value["semantics"]["recorded_constraint_projection_is_not_validation"] is True
    assert value["semantics"]["omitted_constraint_is_unknown_not_unrestricted"] is True


def test_constraint_projection_preserves_presence_without_inventing_validity(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "principal:alice", AuthoritySubjectKind.PRINCIPAL)
    _subject(store, "connector:github", AuthoritySubjectKind.CONNECTOR)
    edge = store.record_edge(
        "principal:alice",
        AuthorityRelationType.DELEGATES,
        "connector:github",
        constraints={
            "issuer": "https://idp.example",
            "tenant": "acme",
            "binding": "device:key-1",
            "expires_at": "2026-09-21T02:00:00Z",
            "repositories": ["acme/app"],
            "mfa_required": True,
            "provider_extension": {"opaque": True},
        },
        evidence=OBSERVED,
    )
    value = explain_authority_path(store, [edge["edge_id"]])
    projection = value["authority_edges"][0]["recorded_constraint_semantics"]
    assert projection == {
        "issuer": "https://idp.example",
        "tenant": "acme",
        "binding": "device:key-1",
        "expires_at": "2026-09-21T02:00:00Z",
        "repositories": ["acme/app"],
        "mfa_required": True,
    }
    assert "scopes" not in projection
    assert "audiences" not in projection
    assert "provider_extension" not in projection
    assert value["authority_edges"][0]["constraints"]["provider_extension"] == {"opaque": True}


def test_supporting_edge_boundary_is_not_projected_as_path_crossing(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    path_edge, support_edge = _fixture(store)
    support_with_boundary = store.record_edge(
        "credential:oauth-1",
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        "principal:alice",
        boundary_refs=["boundary:idp"],
        evidence=OBSERVED,
    )
    value = explain_authority_path(store, [path_edge["edge_id"]], supporting_edge_ids=[support_with_boundary["edge_id"]])

    assert [item["boundary_ref"] for item in value["trust_boundary_crossings"]] == ["boundary:github"]
    assert value["trust_boundary_refs"] == ["boundary:github", "boundary:idp"]
    assert support_edge["edge_id"] not in value["edge_ids"]
