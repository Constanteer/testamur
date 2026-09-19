from __future__ import annotations

from typing import Any

from .authority_product_service import (
    AuthorityProductService,
    authority_blast_product,
    authority_reach_product,
)


def authority_reach_cli(
    service: AuthorityProductService,
    ref: str,
    *,
    compromise_model: str,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Return the canonical product projection for ``authority reach``.

    CLI code must not reinterpret raw authority-engine payloads.  In particular,
    connectivity, material lineage, reliance, and affectedness are not permission
    evidence, and unresolved constraints remain blocked.
    """
    return authority_reach_product(
        service,
        ref,
        compromise_model=compromise_model,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )


def authority_blast_cli(
    service: AuthorityProductService,
    refs: list[str],
    *,
    compromise_model: str,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Return the canonical product projection for explicit compromise seeds."""
    return authority_blast_product(
        service,
        refs,
        compromise_model=compromise_model,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )


__all__ = ["authority_blast_cli", "authority_reach_cli"]
