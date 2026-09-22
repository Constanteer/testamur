from __future__ import annotations

from typing import Any, Mapping, Sequence

from .authority_boundaries import aggregate_trust_boundary_crossings, boundary_refs_from_crossings
from .authority_projection import capability_identity


def _seed_refs(item: Mapping[str, Any], seed_ref: str) -> list[str]:
    """Return provenance that is valid for this exact per-seed traversal."""
    seed = str(seed_ref).strip()
    recorded = item.get("compromise_seed_refs")
    if recorded is None:
        return [seed] if seed else []
    if not isinstance(recorded, Sequence) or isinstance(recorded, (str, bytes)):
        raise ValueError("compromise_seed_refs must be a sequence")
    refs = {str(ref).strip() for ref in recorded if str(ref).strip()}
    if not seed:
        return sorted(refs)
    if refs - {seed}:
        raise ValueError("nested compromise seed provenance does not match traversal seed")
    return [seed]


def _merge_record(existing: dict[str, Any] | None, item: Mapping[str, Any], seed_ref: str) -> dict[str, Any]:
    merged = dict(item) if existing is None else dict(existing)
    existing_refs = existing.get("compromise_seed_refs") if existing else []
    if existing_refs is None:
        existing_refs = []
    if not isinstance(existing_refs, Sequence) or isinstance(existing_refs, (str, bytes)):
        raise ValueError("aggregated compromise_seed_refs must be a sequence")
    merged["compromise_seed_refs"] = sorted({
        *(str(ref).strip() for ref in existing_refs if str(ref).strip()),
        *_seed_refs(item, seed_ref),
    })
    return merged


def aggregate_seeded_blast_results(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate per-seed reachability without inventing cross-seed authority.

    Records are merged only when their canonical identity and exact authority path
    match. Trust-boundary crossings are first bound to their actual traversal seed,
    then passed through the shared canonical boundary aggregator. This keeps
    reachability, blast, ProductService, and Web consumers on one exact crossing
    identity instead of maintaining subtly different edge/boundary dedup rules.
    Connectivity, material lineage, reliance, and affectedness never create either
    authority or crossing provenance.
    """
    subjects: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    actions: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    blocked: dict[tuple[str, str, str, tuple[str, ...]], dict[str, Any]] = {}
    seeded_crossings: list[dict[str, Any]] = []
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
                seeded_crossings.append(_merge_record(None, crossing, seed_ref))

        for reason in result.get("truncation_reasons") or []:
            text = str(reason).strip()
            if text:
                truncation_reasons.add(text)

    crossing_values = aggregate_trust_boundary_crossings(seeded_crossings)
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
            "nested_seed_provenance_is_bound_to_traversal_seed": True,
            "same_target_does_not_merge_distinct_paths": True,
            "material_lineage_does_not_create_seed_provenance": True,
            "trust_boundary_crossings_are_engine_recorded_not_reconstructed": True,
            "trust_boundary_crossing_seed_provenance_is_engine_recorded": True,
            "trust_boundary_crossings_preserve_exact_path_identity": True,
            "trust_boundary_crossings_use_canonical_aggregation": True,
            "truncation_is_union_of_per_seed_engine_results": True,
        },
    }


def build_blast_radius_result(
    results: Sequence[Mapping[str, Any]],
    *,
    compromised_refs: Sequence[str],
    compromise_model: str,
) -> dict[str, Any]:
    """Build the canonical blast-radius envelope from per-seed engine results."""
    seeds = sorted({str(ref).strip() for ref in compromised_refs if str(ref).strip()})
    if not seeds:
        raise ValueError("compromised_refs must contain at least one subject ref")

    result_seeds: list[str] = []
    for result in results:
        seed_ref = str(result.get("starting_subject_ref") or "").strip()
        if not seed_ref:
            raise ValueError("reachability result missing starting_subject_ref")
        result_seeds.append(seed_ref)
    if len(result_seeds) != len(set(result_seeds)):
        raise ValueError("duplicate reachability result for compromise seed")
    if set(result_seeds) != set(seeds):
        raise ValueError("reachability results must correspond exactly to compromised_refs")

    aggregated = aggregate_seeded_blast_results(results)
    helper_semantics = dict(aggregated.pop("semantics", {}))
    return {
        "schema_version": "testamur.authority-blast-radius.v1",
        "compromised_refs": seeds,
        "compromise_model": str(compromise_model),
        **aggregated,
        "semantics": {
            "blast_radius_is_potential_authority_not_observed_malicious_use": True,
            "affectedness_does_not_automatically_seed_compromise": True,
            "material_lineage_does_not_grant_authority": True,
            "blast_results_are_bound_to_explicit_compromise_seeds": True,
            **helper_semantics,
        },
    }


__all__ = ["aggregate_seeded_blast_results", "build_blast_radius_result"]
