from __future__ import annotations

from typing import Any, Mapping, Sequence

from .authority_capability import CapabilityBudget
from .authority_projection import capability_identity, projected_budget_identity


def _exact_ref(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an exact non-empty string")
    return value.strip()


def _exact_path(path_edge_ids: Sequence[str]) -> tuple[str, ...]:
    if isinstance(path_edge_ids, (str, bytes, bytearray)):
        raise ValueError("path_edge_ids must be a sequence of exact edge refs")
    return tuple(_exact_ref(edge_id, "path_edge_ids") for edge_id in path_edge_ids)


def exact_action_result_identity(
    target_ref: str,
    capability: Mapping[str, Any],
    path_edge_ids: Sequence[str],
) -> tuple[str, str, tuple[str, ...]]:
    """Build dedupe identity without manufacturing authority refs by coercion.

    Identity construction is not evidence normalization. A malformed target/path
    therefore fails closed instead of becoming a different, stringified authority
    state that traversal could later treat as reachable.
    """
    return (
        _exact_ref(target_ref, "target_ref"),
        capability_identity(capability),
        _exact_path(path_edge_ids),
    )


def exact_traversal_state_identity(
    subject_ref: str,
    reachability_class: str,
    budget: CapabilityBudget | None,
    path_edge_ids: Sequence[str],
) -> tuple[str, str, tuple[str, ...] | None, tuple[str, ...]]:
    """Build traversal-state identity from exact refs only.

    This does not search the graph and cannot derive authority from connectivity,
    lineage, reliance, or affectedness.
    """
    return (
        _exact_ref(subject_ref, "subject_ref"),
        _exact_ref(reachability_class, "reachability_class"),
        projected_budget_identity(budget),
        _exact_path(path_edge_ids),
    )


__all__ = ["exact_action_result_identity", "exact_traversal_state_identity"]
