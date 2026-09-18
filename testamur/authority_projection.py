from __future__ import annotations

import json
from typing import Any, Mapping

from .authority_capability import CapabilityBudget, project_budget


def capability_identity(capability: Mapping[str, Any]) -> str:
    """Return a stable identity for an exact effective capability.

    Authority deduplication must include constraints. Two capabilities with the same
    namespace/action/resource but different audience, scope, tenant, approval, or
    binding constraints are not interchangeable authority observations.
    """
    return json.dumps(
        dict(capability),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def projected_budget_identity(budget: CapabilityBudget | None) -> tuple[str, ...] | None:
    """Stable path-state identity without discarding delegated constraints."""
    projected = project_budget(budget)
    if projected is None:
        return None
    return tuple(sorted(capability_identity(item) for item in projected))


def project_authority_budget(budget: CapabilityBudget | None) -> list[dict[str, Any]] | None:
    """Product/CLI/Web projection for the exact effective delegated authority."""
    return project_budget(budget)


__all__ = [
    "capability_identity",
    "projected_budget_identity",
    "project_authority_budget",
]
