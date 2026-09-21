from __future__ import annotations

from typing import Any, Iterable

from .authority import TestamurAuthorityStore


def project_trust_boundary_crossings(
    store: TestamurAuthorityStore,
    edge_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Project only trust-boundary crossings explicitly attached to authority edges.

    Boundary membership is not authority and graph connectivity is not a crossing.
    A crossing exists here only when the exact traversed authority edge carries the
    boundary reference. This deliberately does not inspect material lineage,
    reliance, affectedness, endpoint domains, or neighboring edges to infer one.

    Every crossing also records the complete traversed authority path. ``edge_id``
    identifies the exact edge carrying the boundary annotation while
    ``path_edge_ids`` preserves the authority path on which that crossing was
    observed. Consumers must not treat the same edge/boundary pair reached through
    a different authority path as equivalent evidence.
    """
    path_edge_ids = tuple(str(raw).strip() for raw in edge_ids if str(raw).strip())
    crossings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for position, edge_id in enumerate(path_edge_ids):
        edge = store.get_edge(edge_id)
        for raw_boundary_ref in edge.get("boundary_refs") or []:
            boundary_ref = str(raw_boundary_ref).strip()
            if not boundary_ref:
                continue
            identity = (edge_id, boundary_ref, position)
            if identity in seen:
                continue
            seen.add(identity)
            crossings.append(
                {
                    "edge_id": edge_id,
                    "boundary_ref": boundary_ref,
                    "path_position": position,
                    "path_edge_ids": list(path_edge_ids),
                    "source_ref": str(edge.get("source_ref") or ""),
                    "target_ref": str(edge.get("target_ref") or ""),
                    "relation_type": str(edge.get("relation_type") or ""),
                }
            )
    return crossings


def boundary_refs_from_crossings(crossings: Iterable[dict[str, Any]]) -> list[str]:
    """Compatibility projection for clients that only need the boundary set."""
    return sorted(
        {
            str(item.get("boundary_ref") or "").strip()
            for item in crossings
            if str(item.get("boundary_ref") or "").strip()
        }
    )


__all__ = ["project_trust_boundary_crossings", "boundary_refs_from_crossings"]
