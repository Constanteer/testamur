from __future__ import annotations

from typing import Any

from .authority_product_service import AuthorityProductService, authority_blast_product, authority_reach_product
from .authority_web_projection import project_authority_web_view


def authority_reach_web(
    service: AuthorityProductService,
    ref: str,
    *,
    compromise_model: str,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Run canonical reachability and return the stable Web view model."""
    product = authority_reach_product(
        service,
        ref,
        compromise_model=compromise_model,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )
    return project_authority_web_view(product)


def authority_blast_web(
    service: AuthorityProductService,
    refs: list[str],
    *,
    compromise_model: str,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Run canonical blast radius for explicit compromise seeds and project it."""
    product = authority_blast_product(
        service,
        refs,
        compromise_model=compromise_model,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )
    return project_authority_web_view(product)


__all__ = ["authority_blast_web", "authority_reach_web"]
