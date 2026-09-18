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
    boundary reference.  This deliberately does not inspect material lineage,
    reliance, affectedness, endpoint domains, or neighboring edges to infer one.
    """
    crossings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for position, raw_edge_id in enumerate(edge_ids):
        edge_id = str(raw_edge_id).strip()
        if not edge_id:
            continue
        edge = store.get_edge(edge_id)
        for raw_boundary_ref in edge.get("boundary_refs") or []:
            boundary_ref = str(raw_boundary_ref).strip()
            if not boundary_ref:
                continue
            identity = (edge_id, boundary_ref)
            if identity in seen:
                continue
            seen.add(identity)
            crossings.append(
                {
                    "edge_id": edge_id,
                    "boundary_ref": boundary_ref,
                    "path_position": position,
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
