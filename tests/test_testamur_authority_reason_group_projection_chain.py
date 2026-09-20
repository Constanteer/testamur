from __future__ import annotations

from testamur.authority_product_projection import project_authority_result
from testamur.authority_web_projection import project_authority_web_view


def _engine_result() -> dict:
    return {
        "schema_version": "testamur.authority-reachability.v1",
        "starting_subject_ref": "credential:seed",
        "reachable_subjects": [],
        "actionable_capabilities": [],
        "blocked_transitions": [
            {
                "edge_id": "edge:blocked",
                "source_ref": "credential:seed",
                "target_ref": "connector:github",
                "relation_type": "CAN_AUTHENTICATE_AS",
                "reasons": ["credential_expired", "provider_specific_unknown_gate"],
                "reason_groups": {
                    "credential_or_token": ["credential_expired"],
                    "capability_or_delegation": [],
                    "approval_or_mfa": [],
                    "trust_boundary_policy": [],
                    "other": ["provider_specific_unknown_gate"],
                },
                "path_edge_ids": ["edge:blocked"],
                "supporting_edge_ids": ["token:exact"],
            }
        ],
        "trust_boundary_crossings": [],
    }


def test_product_projection_preserves_engine_reason_groups_without_reclassification():
    projected = project_authority_result(_engine_result())
    blocked = projected["diagnostics"]["blocked_transitions"][0]

    assert blocked["reason_groups"] == {
        "credential_or_token": ["credential_expired"],
        "capability_or_delegation": [],
        "approval_or_mfa": [],
        "trust_boundary_policy": [],
        "other": ["provider_specific_unknown_gate"],
    }
    assert projected["diagnostics"]["semantics"][
        "reason_groups_are_engine_recorded_not_product_inferred"
    ] is True


def test_web_projection_preserves_product_reason_groups_for_canonical_renderer():
    product = project_authority_result(_engine_result())
    web = project_authority_web_view(
        {
            "ok": True,
            "schema": "testamur.product.authority-result.v1",
            "result": product,
        }
    )
    blocked = web["blocked_transitions"][0]

    assert blocked["reason_groups"]["credential_or_token"] == ["credential_expired"]
    assert blocked["reason_groups"]["other"] == ["provider_specific_unknown_gate"]
    assert web["semantics"]["reason_groups_are_canonical_not_web_inferred"] is True


def test_missing_reason_groups_stays_unclassified_instead_of_guessing_from_reason_text():
    raw = _engine_result()
    raw["blocked_transitions"][0].pop("reason_groups")
    projected = project_authority_result(raw)
    groups = projected["diagnostics"]["blocked_transitions"][0]["reason_groups"]

    assert all(not values for values in groups.values())
    assert projected["diagnostics"]["blocked_transitions"][0]["reasons"] == [
        "credential_expired",
        "provider_specific_unknown_gate",
    ]
