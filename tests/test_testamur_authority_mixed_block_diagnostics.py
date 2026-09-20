from __future__ import annotations

from unittest.mock import patch

from testamur.authority_reachability import _enrich_blocked


class _Store:
    def get_edge(self, edge_id: str):
        assert edge_id == "edge:candidate"
        return {
            "edge_id": edge_id,
            "relation_type": "CAN_WRITE",
            "capabilities": [
                {
                    "namespace": "github",
                    "action": "write",
                    "resource": "org/other-repo",
                    "constraints": {"audience": "api.github.com"},
                }
            ],
        }


def test_mixed_block_reasons_keep_independent_reason_and_exact_capability_diagnostic():
    result = {
        "blocked_transitions": [
            {
                "edge_id": "edge:candidate",
                "path_edge_ids": ["edge:candidate"],
                "reasons": [
                    "missing_explicit_or_authorized_capability",
                    "approval_gate_unsatisfied",
                ],
            }
        ]
    }
    diagnostic = {
        "reasons": ["audience_outside_delegation"],
        "failed_constraints": ["audience"],
        "unresolved_constraints": [],
        "candidate_capabilities": [{"namespace": "github", "action": "write"}],
        "inherited_capability_budget": [{"namespace": "github", "action": "write"}],
    }

    with patch(
        "testamur.authority_reachability.capability_rejection_diagnostics",
        return_value=diagnostic,
    ):
        enriched = _enrich_blocked(_Store(), result)

    blocked = enriched["blocked_transitions"][0]
    assert blocked["reasons"] == [
        "approval_gate_unsatisfied",
        "audience_outside_delegation",
    ]
    assert blocked["failed_constraints"] == ["audience"]
    assert blocked["unresolved_constraints"] == []
    assert blocked["candidate_capabilities"] == diagnostic["candidate_capabilities"]
    assert blocked["inherited_capability_budget"] == diagnostic["inherited_capability_budget"]


def test_non_capability_block_is_not_reinterpreted_as_authority_failure():
    result = {
        "blocked_transitions": [
            {
                "edge_id": "edge:candidate",
                "path_edge_ids": ["edge:candidate"],
                "reasons": ["credential_expired"],
            }
        ]
    }

    with patch(
        "testamur.authority_reachability.capability_rejection_diagnostics"
    ) as diagnostics:
        enriched = _enrich_blocked(_Store(), result)

    assert enriched == result
    diagnostics.assert_not_called()
