from __future__ import annotations

from typing import Any, Protocol

from .authority_product_api import project_product_authority_envelope


class AuthorityProductService(Protocol):
    """Minimal ProductService surface needed by authority projections."""

    def authority_reach(self, ref: str, **options: Any) -> dict[str, Any]: ...

    def authority_blast(self, refs: list[str], **options: Any) -> dict[str, Any]: ...


def authority_reach_product(
    service: AuthorityProductService,
    ref: str,
    *,
    compromise_model: str,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Return the stable CLI/Web projection for one compromise seed.

    The service remains responsible for canonical object lookup and the authority
    engine remains responsible for reachability.  This facade only projects the
    successful authority envelope; it never reconstructs permissions from graph
    connectivity, lineage, reliance, or affectedness.
    """
    envelope = service.authority_reach(
        ref,
        compromise_model=compromise_model,
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
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Return the stable CLI/Web projection for explicit compromise seeds only."""
    envelope = service.authority_blast(
        refs,
        compromise_model=compromise_model,
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
