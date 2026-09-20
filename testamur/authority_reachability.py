"""Canonical authority compromise reachability.

The implementation lives in ``authority_reachability_v2`` so the legacy tuple-budget
engine cannot silently reintroduce connectivity-as-permission or drop capability
constraints. This module remains the stable public import surface and enriches
blocked results with denial diagnostics derived from the exact traversed path.
"""

from __future__ import annotations

from typing import Any, Mapping

from .authority import AuthorityRelationType, TestamurAuthorityStore
from .authority_reachability_policy import capability_rejection_diagnostics, downstream_budget
from .authority_reachability_v2 import (
    AuthorityReachabilityClass,
    CompromiseModel,
    authority_blast_radius as _authority_blast_radius,
    authority_reachability as _authority_reachability,
)


def _budget_before_final_edge(store: TestamurAuthorityStore, path_edge_ids: list[str]):
    """Replay only canonical budget propagation for diagnostic attribution.

    This does not decide reachability. The v2 engine already made that decision;
    replay is restricted to the exact recorded path so diagnostics can expose the
    inherited delegation that rejected a candidate capability.
    """
    budget = None
    for edge_id in path_edge_ids[:-1]:
        edge = store.get_edge(edge_id)
        relation = str(edge.get("relation_type") or "")
        if relation == AuthorityRelationType.DELEGATES.value:
            budget = downstream_budget(edge, budget)
        elif relation in {
            AuthorityRelationType.CAN_AUTHENTICATE_AS.value,
            AuthorityRelationType.CAN_IMPERSONATE.value,
        }:
            budget = downstream_budget(edge, None)
    return budget


def _enrich_blocked(store: TestamurAuthorityStore, result: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(result)
    blocked: list[dict[str, Any]] = []
    for raw in result.get("blocked_transitions") or []:
        item = dict(raw)
        reasons = [str(value) for value in item.get("reasons") or [] if str(value)]
        # A transition may carry more than one canonical blocking reason. Capability
        # diagnostics must not disappear merely because the engine also recorded an
        # independent gate/validity reason. Diagnostics explain the exact recorded
        # candidate edge; they never turn that edge into authority.
        if "missing_explicit_or_authorized_capability" in reasons:
            path = [str(value) for value in item.get("path_edge_ids") or [] if str(value)]
            if path:
                edge = store.get_edge(path[-1])
                diagnostic = capability_rejection_diagnostics(
                    edge, _budget_before_final_edge(store, path)
                )
                if diagnostic is not None:
                    diagnostic_reasons = [
                        str(value) for value in diagnostic.get("reasons") or [] if str(value)
                    ]
                    item["reasons"] = list(
                        dict.fromkeys(
                            reason
                            for reason in reasons
                            if reason != "missing_explicit_or_authorized_capability"
                        )
                    )
                    item["reasons"].extend(
                        reason
                        for reason in diagnostic_reasons
                        if reason not in item["reasons"]
                    )
                    item["failed_constraints"] = diagnostic["failed_constraints"]
                    item["unresolved_constraints"] = diagnostic["unresolved_constraints"]
                    item["candidate_capabilities"] = diagnostic["candidate_capabilities"]
                    item["inherited_capability_budget"] = diagnostic["inherited_capability_budget"]
        blocked.append(item)
    enriched["blocked_transitions"] = blocked
    return enriched


def authority_reachability(store: TestamurAuthorityStore, *args, **kwargs):
    return _enrich_blocked(store, _authority_reachability(store, *args, **kwargs))


def authority_blast_radius(store: TestamurAuthorityStore, *args, **kwargs):
    return _enrich_blocked(store, _authority_blast_radius(store, *args, **kwargs))


__all__ = [
    "CompromiseModel",
    "AuthorityReachabilityClass",
    "authority_reachability",
    "authority_blast_radius",
]
