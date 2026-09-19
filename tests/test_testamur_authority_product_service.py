from __future__ import annotations

from testamur.authority_product_service import authority_blast_product, authority_reach_product


class FakeService:
    def __init__(self, reach=None, blast=None):
        self.reach = reach
        self.blast = blast
        self.calls = []

    def authority_reach(self, ref, **options):
        self.calls.append(("reach", ref, options))
        return self.reach

    def authority_blast(self, refs, **options):
        self.calls.append(("blast", list(refs), options))
        return self.blast


def _engine_result(schema_version: str):
    return {
        "schema_version": schema_version,
        "starting_subject_ref": "subject:token",
        "compromise_model": "credential_theft",
        "reachable_subjects": [],
        "actionable_capabilities": [
            {
                "namespace": "github",
                "action": "write",
                "resource": "repo:Constanteer/testamur",
                "constraints": {
                    "audience": ["github.com"],
                    "scope": ["contents:write"],
                    "tenant": "Constanteer",
                },
            }
        ],
        "blocked_transitions": [],
        "trust_boundary_crossings": [],
    }


def test_reach_facade_projects_constraints_without_reinterpreting_them():
    service = FakeService(
        reach={
            "ok": True,
            "schema": "testamur.product.authority-reachability.v1",
            "result": _engine_result("testamur.authority-reachability.v1"),
        }
    )
    result = authority_reach_product(
        service,
        "subject:token",
        compromise_model="credential_theft",
        max_depth=4,
        as_of="2026-09-19T00:00:00Z",
    )
    assert result["schema"] == "testamur.product.authority-result.v1"
    assert result["operation_schema"] == "testamur.product.authority-reachability.v1"
    capability = result["result"]["actionable_capabilities"][0]
    assert capability["constraints"]["scope"] == ["contents:write"]
    assert capability["constraints"]["audience"] == ["github.com"]
    assert capability["constraints"]["tenant"] == "Constanteer"
    assert service.calls[0][2]["max_depth"] == 4


def test_facade_preserves_product_service_errors_exactly():
    error = {
        "ok": False,
        "schema": "testamur.error.v1",
        "error": {"code": "object_not_found", "message": "missing", "details": {"ref": "subject:nope"}},
    }
    service = FakeService(reach=error)
    assert authority_reach_product(
        service, "subject:nope", compromise_model="credential_theft"
    ) == error


def test_blast_facade_projects_only_explicit_seed_result():
    engine = _engine_result("testamur.authority-blast-radius.v1")
    engine.pop("starting_subject_ref")
    engine["compromised_refs"] = ["subject:a", "subject:b"]
    engine["semantics"] = {
        "affectedness_does_not_seed_compromise": True,
        "material_lineage_does_not_grant_authority": True,
    }
    service = FakeService(
        blast={
            "ok": True,
            "schema": "testamur.product.authority-blast-radius.v1",
            "result": engine,
        }
    )
    result = authority_blast_product(
        service,
        ["subject:a", "subject:b"],
        compromise_model="credential_theft",
    )
    assert result["schema"] == "testamur.product.authority-result.v1"
    assert result["semantics"]["affectedness_does_not_seed_compromise"] is True
    assert result["result"]["compromised_refs"] == ["subject:a", "subject:b"]
    assert service.calls[0][1] == ["subject:a", "subject:b"]
