from __future__ import annotations

from typing import Any, Mapping


def exact_nonempty_string(value: Any, *, field: str) -> str:
    """Validate identity-bearing authority evidence without coercion."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an exact non-empty string")
    return value.strip()


def exact_authority_edge_identity(edge: Mapping[str, Any]) -> tuple[str, str, str, str]:
    """Return (edge_id, source_ref, target_ref, relation_type) exactly as evidenced.

    This helper intentionally performs no graph lookup.  Connectivity, lineage,
    reliance, or affectedness cannot repair a malformed authority edge identity.
    """
    if not isinstance(edge, Mapping):
        raise ValueError("authority edge must be a mapping")
    return (
        exact_nonempty_string(edge.get("edge_id"), field="edge_id"),
        exact_nonempty_string(edge.get("source_ref"), field="source_ref"),
        exact_nonempty_string(edge.get("target_ref"), field="target_ref"),
        exact_nonempty_string(edge.get("relation_type"), field="relation_type"),
    )


def exact_optional_constraint_ref(value: Any, *, field: str) -> str | None:
    """Validate an optional binding ref; present malformed evidence fails closed."""
    if value is None:
        return None
    return exact_nonempty_string(value, field=field)


__all__ = ["exact_nonempty_string", "exact_authority_edge_identity", "exact_optional_constraint_ref"]
