from __future__ import annotations

from typing import Any, Protocol

from .authority_filter import normalize_capability_filter
from .authority_product_api import project_product_authority_envelope


class AuthorityProductService(Protocol):
    """Minimal ProductService surface needed by authority projections."""

    def authority_reach(self, ref: str, **options: Any) -> dict[str, Any]: ...

    def authority_blast(self, refs: list[str], **options: Any) -> dict[str, Any]: ...


def _canonical_service_reach(
    service: AuthorityProductService,
    ref: str,
    *,
    compromise_model: str,
    capability_filter: list[tuple[str, str]],
    max_depth: int,
    max_paths: int,
    expansion_budget: int,
    as_of: str | None,
) -> dict[str, Any]:
    """Bridge the concrete ProductService to the canonical authority engine.

    Older ProductService method signatures predate capability selectors.  When the
    concrete service exposes its canonical authority store, use that store directly
    rather than dropping the selector or reconstructing permissions in this facade.
    Other protocol implementations continue through their declared service method.
    """
    store = getattr(service, "authority", None)
    if store is None:
        return service.authority_reach(
            ref,
            compromise_model=compromise_model,
            capability_filter=capability_filter,
            max_depth=max_depth,
            max_paths=max_paths,
            expansion_budget=expansion_budget,
            as_of=as_of,
        )

    from .authority_reachability import authority_reachability
    from .contracts import error_envelope

    if store.maybe_subject(ref) is None:
        return error_envelope(
            "object_not_found",
            "no canonical authority subject exists for this reference",
            details={"ref": ref},
        )
    result = authority_reachability(
        store,
        ref,
        compromise_model=compromise_model,
        capability_filter=capability_filter,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )
    return {
        "ok": True,
        "schema": "testamur.product.authority-reachability.v1",
        "result": result,
    }


def _canonical_service_blast(
    service: AuthorityProductService,
    refs: list[str],
    *,
    compromise_model: str,
    capability_filter: list[tuple[str, str]],
    max_depth: int,
    max_paths: int,
    expansion_budget: int,
    as_of: str | None,
) -> dict[str, Any]:
    """Blast-radius counterpart of ``_canonical_service_reach``."""
    store = getattr(service, "authority", None)
    if store is None:
        return service.authority_blast(
            refs,
            compromise_model=compromise_model,
            capability_filter=capability_filter,
            max_depth=max_depth,
            max_paths=max_paths,
            expansion_budget=expansion_budget,
            as_of=as_of,
        )

    from .authority_reachability import authority_blast_radius
    from .contracts import error_envelope

    missing = [ref for ref in refs if store.maybe_subject(ref) is None]
    if missing:
        return error_envelope(
            "object_not_found",
            "one or more canonical authority subjects do not exist",
            details={"refs": missing},
        )
    result = authority_blast_radius(
        store,
        refs,
        compromise_model=compromise_model,
        capability_filter=capability_filter,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )
    return {
        "ok": True,
        "schema": "testamur.product.authority-blast-radius.v1",
        "result": result,
    }


def authority_reach_product(
    service: AuthorityProductService,
    ref: str,
    *,
    compromise_model: str,
    capability_filter: list[tuple[str, str]] | None = None,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Return the stable CLI/Web projection for one compromise seed.

    The canonical authority engine remains responsible for reachability. This
    facade never reconstructs permissions from graph connectivity, lineage,
    reliance, or affectedness. Capability filters are explicit namespace/action
    selectors, not permission grants or wildcards.
    """
    normalized_filter = normalize_capability_filter(capability_filter)
    envelope = _canonical_service_reach(
        service,
        ref,
        compromise_model=compromise_model,
        capability_filter=normalized_filter,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )
    return project_product_authority_envelope(envelope)


def authority_blast_product(
    service: AuthorityProductService,
    refs: list[str],
    *,
    compromise_model: str,
    capability_filter: list[tuple[str, str]] | None = None,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Return the stable CLI/Web projection for explicit compromise seeds only."""
    normalized_filter = normalize_capability_filter(capability_filter)
    envelope = _canonical_service_blast(
        service,
        refs,
        compromise_model=compromise_model,
        capability_filter=normalized_filter,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )
    return project_product_authority_envelope(envelope)


__all__ = [
    "AuthorityProductService",
    "authority_blast_product",
    "authority_reach_product",
]
