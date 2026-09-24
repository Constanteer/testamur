from __future__ import annotations

import pytest

from testamur.authority_cli_projection import (
    authority_blast_cli,
    authority_explain_cli,
    authority_reach_cli,
    authority_subject_cli,
)


class RecordingService:
    def __init__(self):
        self.calls = []

    def authority_subject(self, ref):
        self.calls.append(("subject", ref))
        return {"ok": True}

    def authority_explain(self, edge_ids, **options):
        self.calls.append(("explain", edge_ids, options))
        return {"ok": True}

    def authority_reach(self, ref, **options):
        self.calls.append(("reach", ref, options))
        return {
            "ok": True,
            "schema": "testamur.product.authority-reachability.v1",
            "result": {
                "schema_version": "testamur.authority-reachability.v1",
                "starting_subject_ref": ref,
                "compromise_model": options["compromise_model"],
                "reachable_subjects": [],
                "actionable_capabilities": [],
                "blocked_transitions": [],
                "trust_boundary_crossings": [],
            },
        }

    def authority_blast(self, refs, **options):
        self.calls.append(("blast", refs, options))
        return {
            "ok": True,
            "schema": "testamur.product.authority-blast-radius.v1",
            "result": {
                "schema_version": "testamur.authority-blast-radius.v1",
                "compromised_refs": refs,
                "compromise_model": options["compromise_model"],
                "reachable_subjects": [],
                "actionable_capabilities": [],
                "blocked_transitions": [],
                "trust_boundary_crossings": [],
            },
        }


def test_subject_cli_rejects_connectivity_shaped_ref():
    service = RecordingService()
    with pytest.raises(ValueError):
        authority_subject_cli(service, {"ref": "subject:a", "connected": True})
    assert service.calls == []


def test_explain_cli_rejects_typed_edge_and_supporting_edge_identity():
    service = RecordingService()
    with pytest.raises(ValueError):
        authority_explain_cli(service, [{"edge_id": "edge:a"}])
    with pytest.raises(ValueError):
        authority_explain_cli(service, ["edge:a"], supporting_edge_ids=[7])
    assert service.calls == []


def test_explain_cli_rejects_typed_path_endpoint_identity():
    service = RecordingService()
    with pytest.raises(ValueError):
        authority_explain_cli(
            service,
            ["edge:a"],
            expected_target_ref={"ref": "subject:b", "reachable": True},
        )
    assert service.calls == []


def test_reach_cli_preserves_exact_selector_without_turning_it_into_authority():
    service = RecordingService()
    result = authority_reach_cli(
        service,
        "subject:a",
        compromise_model="credential_theft",
        capability_filter=[("github", "read")],
    )
    assert result["decision"]["compromise_seeds"] == ["subject:a"]
    assert service.calls[0][2]["capability_filter"] == [("github", "read")]


def test_blast_cli_rejects_affectedness_shaped_compromise_seed():
    service = RecordingService()
    with pytest.raises(ValueError):
        authority_blast_cli(
            service,
            [{"ref": "subject:a", "affected": True}],
            compromise_model="credential_theft",
        )
    assert service.calls == []
