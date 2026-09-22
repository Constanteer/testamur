from __future__ import annotations

from typing import Any, Protocol

from .authority_product_api import project_product_authority_envelope


class AuthorityProductService(Protocol):
    """Minimal ProductService surface needed by authority projections."""

    def authority_reach(self, ref: str, **options: Any) -> dict[str, Any]: ...

    def authority_blast(self, refs: list[str], **options: Any) -> dict[str, Any]: ...


def _capability_filter(value: list[tuple[str, str]] | None) -> list[tuple[str, str]] | None:
    """Validate an explicit namespace/action filter without inventing wildcard authority."""
    if value is None:
        return None
    normalized: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError("capability_filter entries must be namespace/action pairs")
        namespace, action = item
        if not isinstance(namespace, str) or not namespace.strip() or not isinstance(action, str) or not action.strip():
            raise ValueError("capability_filter namespace/action values must be non-empty strings")
        normalized.append((namespace.strip(), action.strip()))
    return normalized


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

    The service remains responsible for canonical object lookup and the authority
    engine remains responsible for reachability.  This facade only projects the
    successful authority envelope; it never reconstructs permissions from graph
    connectivity, lineage, reliance, or affectedness. Capability filters are
    explicit namespace/action selectors, not permission grants or wildcards.
    """
    envelope = service.authority_reach(
        ref,
        compromise_model=compromise_model,
        capability_filter=_capability_filter(capability_filter),
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
    envelope = service.authority_blast(
        refs,
        compromise_model=compromise_model,
        capability_filter=_capability_filter(capability_filter),
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
