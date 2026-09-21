from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from .authority import TestamurAuthorityStore
from .authority_blast_provenance import build_blast_radius_result


_REACHABILITY_SCHEMA_VERSION = "testamur.authority-reachability.v1"


def canonical_authority_blast_radius(
    store: TestamurAuthorityStore,
    compromised_refs: str | Sequence[str],
    *,
    compromise_model: str,
    capability_filter: Iterable[tuple[str, str]] | None = None,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | datetime | None = None,
) -> dict[str, Any]:
    """Run one exact authority-reachability traversal per explicit compromise seed.

    This orchestration deliberately does not combine graphs before traversal. Each
    seed is evaluated independently by the authority engine and only the recorded
    per-seed results are aggregated afterwards. Material lineage, reliance,
    affectedness, common targets, and graph connectivity therefore cannot create
    compromise-seed provenance or authority that the engine did not record.

    A blast evaluation also has one temporal observation point. When callers do
    not supply ``as_of``, snapshot UTC once here and pass that same instant to
    every seed traversal. Credential expiry, token audience/scope constraints,
    acceptance edges, and delegated permissions therefore cannot disagree merely
    because separate seed traversals happened on opposite sides of a time boundary.
    The normalized observation instant emitted by reachability is required to be
    identical for every seed and is preserved on the blast envelope for audit.

    Reachability results are also bound to the normalized compromise model used
    for this evaluation. A result produced under another compromise assumption
    cannot be mixed into the same blast envelope, even if its seed/path happens
    to match. This keeps model assumptions as provenance rather than presentation.

    Finally, every returned reachability envelope is bound to the exact seed whose
    traversal produced it. Merely returning the right *set* of seed refs is not
    sufficient: a swapped or mislabeled result would attach exact evidence and
    capabilities to the wrong compromise assumption. The schema version is also
    checked before aggregation so an unrelated projection cannot masquerade as an
    engine reachability result.
    """
    # Local import avoids making the reachability module depend on this orchestration
    # while it still exposes the legacy authority_blast_radius entry point.
    from .authority_reachability_v2 import _normalize_model, authority_reachability

    refs = [compromised_refs] if isinstance(compromised_refs, str) else list(compromised_refs)
    seeds = sorted({str(ref).strip() for ref in refs if str(ref).strip()})
    if not seeds:
        raise ValueError("compromised_refs must contain at least one subject ref")

    model = _normalize_model(compromise_model)
    evaluation_as_of: str | datetime = as_of if as_of is not None else datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    for seed_ref in seeds:
        result = authority_reachability(
            store,
            seed_ref,
            compromise_model=model,
            capability_filter=capability_filter,
            max_depth=max_depth,
            max_paths=max_paths,
            expansion_budget=expansion_budget,
            as_of=evaluation_as_of,
        )
        if str(result.get("schema_version") or "").strip() != _REACHABILITY_SCHEMA_VERSION:
            raise ValueError("authority reachability returned an unsupported schema version")
        if str(result.get("starting_subject_ref") or "").strip() != seed_ref:
            raise ValueError("authority reachability result does not match requested compromise seed")
        results.append(result)

    observation_instants = {str(result.get("as_of") or "").strip() for result in results}
    if "" in observation_instants or len(observation_instants) != 1:
        raise ValueError("all reachability results must record one identical as_of instant")

    result_models = {str(result.get("compromise_model") or "").strip() for result in results}
    if result_models != {model}:
        raise ValueError("all reachability results must record the requested compromise model")

    envelope = build_blast_radius_result(
        results,
        compromised_refs=seeds,
        compromise_model=model,
    )
    envelope["as_of"] = next(iter(observation_instants))
    envelope["semantics"] = {
        **dict(envelope.get("semantics") or {}),
        "blast_results_share_one_observation_instant": True,
        "blast_results_are_bound_to_one_compromise_model": True,
        "blast_results_are_bound_to_requested_seed_traversals": True,
        "blast_results_require_authority_reachability_schema": True,
    }
    return envelope


__all__ = ["canonical_authority_blast_radius"]