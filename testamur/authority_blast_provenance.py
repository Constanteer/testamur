from __future__ import annotations

from typing import Any, Mapping, Sequence

from .authority_boundaries import boundary_refs_from_crossings
from .authority_projection import capability_identity


def _seed_refs(item: Mapping[str, Any], seed_ref: str) -> list[str]:
    """Return only explicitly supplied seed provenance plus the current engine seed."""
    recorded = item.get("compromise_seed_refs")
    refs = {str(seed_ref).strip()} if str(seed_ref).strip() else set()
    if isinstance(recorded, Sequence) and not isinstance(recorded, (str, bytes)):
        refs.update(str(ref).strip() for ref in recorded if str(ref).strip())
    return sorted(refs)


def _merge_record(existing: dict[str, Any] | None, item: Mapping[str, Any], seed_ref: str) -> dict[str, Any]:
    merged = dict(item) if existing is None else dict(existing)
    merged["compromise_seed_refs"] = sorted({
        *(_seed_refs(existing or {}, "")),
        *_seed_refs(item, seed_ref),
    })
    return merged


def aggregate_seeded_blast_results(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate per-seed reachability without inventing cross-seed authority.

    Each result must be an engine reachability result with ``starting_subject_ref``.
    Records are merged only when their canonical identity *and exact path* match.
    Seed provenance is unioned for such duplicate records. Connectivity, common
    targets, material lineage, reliance, and affectedness never create provenance.

    Aggregate metadata is likewise copied only from engine-recorded reachability
    results: trust-boundary crossings are deduplicated by exact edge/boundary pair,
    and truncation is the union of recorded per-seed truncation reasons. Neither is
    reconstructed from graph adjacency.
    """
    subjects: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    actions: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    blocked: dict[tuple[str, str, str, tuple[str, ...]], dict[str, Any]] = {}
    crossings: dict[tuple[str, str], dict[str, Any]] = {}
    truncation_reasons: set[str] = set()

    for result in results:
        seed_ref = str(result.get("starting_subject_ref") or "").strip()
        if not seed_ref:
            raise ValueError("reachability result missing starting_subject_ref")

        for item in result.get("reachable_subjects") or []:
            key = (str(item.get("subject_ref") or ""), tuple(item.get("path_edge_ids") or []))
            subjects[key] = _merge_record(subjects.get(key), item, seed_ref)

        for item in result.get("actionable_capabilities") or []:
            key = (
                str(item.get("target_ref") or ""),
                capability_identity(item.get("capability") or {}),
                tuple(item.get("path_edge_ids") or []),
            )
            actions[key] = _merge_record(actions.get(key), item, seed_ref)

        for item in result.get("blocked_transitions") or []:
            key = (
                str(item.get("edge_id") or ""),
                str(item.get("source_ref") or ""),
                str(item.get("target_ref") or ""),
                tuple(item.get("path_edge_ids") or []),
            )
            blocked[key] = _merge_record(blocked.get(key), item, seed_ref)

        for crossing in result.get("trust_boundary_crossings") or []:
            if not isinstance(crossing, Mapping):
                continue
            edge_id = str(crossing.get("edge_id") or "").strip()
            boundary_ref = str(crossing.get("boundary_ref") or "").strip()
            if edge_id and boundary_ref:
                crossings[(edge_id, boundary_ref)] = dict(crossing)

        for reason in result.get("truncation_reasons") or []:
            text = str(reason).strip()
            if text:
                truncation_reasons.add(text)

    crossing_values = sorted(
        crossings.values(),
        key=lambda item: (
            int(item.get("path_position") or 0),
            str(item.get("edge_id") or ""),
            str(item.get("boundary_ref") or ""),
        ),
    )
    truncation_values = sorted(truncation_reasons)

    return {
        "reachable_subjects": sorted(
            subjects.values(),
            key=lambda item: (int(item.get("depth") or 0), str(item.get("subject_ref") or ""), tuple(item.get("path_edge_ids") or [])),
        ),
        "actionable_capabilities": sorted(
            actions.values(),
            key=lambda item: (str(item.get("target_ref") or ""), capability_identity(item.get("capability") or {}), tuple(item.get("path_edge_ids") or [])),
        ),
        "blocked_transitions": sorted(
            blocked.values(),
            key=lambda item: (str(item.get("edge_id") or ""), str(item.get("source_ref") or ""), str(item.get("target_ref") or ""), tuple(item.get("path_edge_ids") or [])),
        ),
        "trust_boundary_refs": boundary_refs_from_crossings(crossing_values),
        "trust_boundary_crossings": crossing_values,
        "truncated": bool(truncation_values),
        "truncation_reasons": truncation_values,
        "semantics": {
            "compromise_seed_provenance_is_engine_recorded": True,
            "same_target_does_not_merge_distinct_paths": True,
            "material_lineage_does_not_create_seed_provenance": True,
            "trust_boundary_crossings_are_engine_recorded_not_reconstructed": True,
            "truncation_is_union_of_per_seed_engine_results": True,
        },
    }


__all__ = ["aggregate_seeded_blast_results"]
