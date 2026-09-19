from __future__ import annotations

from testamur.authority_cli_projection import authority_blast_cli, authority_reach_cli


class FakeAuthorityService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, dict[str, object]]] = []

    def authority_reach(self, ref: str, **options: object) -> dict[str, object]:
        self.calls.append(("reach", ref, options))
        return {
            "ok": True,
            "schema": "testamur.product.authority-reachability.v1",
            "result": {
                "schema_version": "testamur.authority-reachability.v1",
                "starting_subject_ref": ref,
                "compromise_model": options["compromise_model"],
                "reachable_subjects": [],
                "actionable_capabilities": [
                    {
                        "namespace": "github",
                        "action": "write",
                        "resource": "repo:Constanteer/testamur",
                        "constraints": {
                            "audience": "github.com",
                            "scopes": ["contents:write"],
                            "tenant": "Constanteer",
                        },
                    }
                ],
                "blocked_transitions": [
                    {
                        "edge_id": "edge:token-to-api",
                        "source_ref": ref,
                        "target_ref": "service:github-api",
                        "relation_type": "AUTHENTICATES_AS",
                        "reasons": ["audience_mismatch"],
                        "unresolved_constraints": ["device_binding"],
                        "path_edge_ids": ["edge:delegation"],
                        "supporting_edge_ids": ["edge:accepts-token"],
                    }
                ],
                "trust_boundary_crossings": [],
            },
        }

    def authority_blast(self, refs: list[str], **options: object) -> dict[str, object]:
        self.calls.append(("blast", list(refs), options))
        return {
            "ok": True,
            "schema": "testamur.product.authority-blast-radius.v1",
            "result": {
                "schema_version": "testamur.authority-blast-radius.v1",
                "compromised_refs": list(refs),
                "compromise_model": options["compromise_model"],
                "reachable_subjects": [],
                "actionable_capabilities": [],
                "blocked_transitions": [],
                "trust_boundary_crossings": [],
            },
        }


def test_cli_reach_uses_stable_projection_without_collapsing_constraints() -> None:
    service = FakeAuthorityService()
    payload = authority_reach_cli(
        service,
        "principal:alice",
        compromise_model="credential_theft",
        max_depth=4,
        as_of="2026-09-19T00:00:00Z",
    )

    assert payload["schema"] == "testamur.product.authority-result.v1"
    capability = payload["result"]["actionable_capabilities"][0]
    assert capability["constraints"] == {
        "audience": "github.com",
        "scopes": ["contents:write"],
        "tenant": "Constanteer",
    }
    blocked = payload["result"]["diagnostics"]["blocked_transitions"][0]
    assert blocked["reasons"] == ["audience_mismatch"]
    assert blocked["unresolved_constraints"] == ["device_binding"]
    assert blocked["path_edge_ids"] == ["edge:delegation"]
    assert blocked["supporting_edge_ids"] == ["edge:accepts-token"]
    assert service.calls[0][2]["max_depth"] == 4
    assert service.calls[0][2]["as_of"] == "2026-09-19T00:00:00Z"


def test_cli_blast_passes_only_explicit_compromise_seeds() -> None:
    service = FakeAuthorityService()
    payload = authority_blast_cli(
        service,
        ["credential:stolen"],
        compromise_model="credential_theft",
    )

    assert payload["schema"] == "testamur.product.authority-result.v1"
    assert payload["result"]["compromised_refs"] == ["credential:stolen"]
    assert payload["result"]["semantics"]["affectedness_does_not_seed_compromise"] is True
    assert service.calls[0][1] == ["credential:stolen"]


def test_cli_facade_preserves_product_errors_exactly() -> None:
    class MissingService(FakeAuthorityService):
        def authority_reach(self, ref: str, **options: object) -> dict[str, object]:
            return {"ok": False, "error": {"code": "object_not_found", "message": ref}}

    payload = authority_reach_cli(
        MissingService(),
        "missing:subject",
        compromise_model="credential_theft",
    )
    assert payload == {
        "ok": False,
        "error": {"code": "object_not_found", "message": "missing:subject"},
    }
