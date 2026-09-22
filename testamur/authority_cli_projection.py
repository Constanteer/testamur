from __future__ import annotations

from typing import Any, Protocol

from .authority_product_service import (
    AuthorityProductService,
    authority_blast_product,
    authority_reach_product,
)


class AuthorityCliService(AuthorityProductService, Protocol):
    """Authority reads exposed to the CLI without reconstructing graph semantics."""

    def authority_subject(self, ref: str) -> dict[str, Any]: ...

    def authority_explain(
        self,
        edge_ids: list[str],
        *,
        starting_ref: str | None = None,
        expected_target_ref: str | None = None,
        supporting_edge_ids: list[str] | None = None,
    ) -> dict[str, Any]: ...


def authority_subject_cli(service: AuthorityCliService, ref: str) -> dict[str, Any]:
    """Inspect one canonical authority subject and its exact recorded edges.

    This is intentionally a pass-through read.  The CLI must not turn adjacency,
    material lineage, reliance, or affectedness into permission evidence.
    """
    if not ref.strip():
        raise ValueError("authority subject requires a non-empty ref")
    return service.authority_subject(ref.strip())


def authority_explain_cli(
    service: AuthorityCliService,
    edge_ids: list[str],
    *,
    starting_ref: str | None = None,
    expected_target_ref: str | None = None,
    supporting_edge_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Explain an explicit ordered authority path plus separate support evidence."""
    exact_edge_ids = [edge_id.strip() for edge_id in edge_ids]
    if not exact_edge_ids or any(not edge_id for edge_id in exact_edge_ids):
        raise ValueError("authority explain requires non-empty exact edge ids")
    exact_support = [edge_id.strip() for edge_id in (supporting_edge_ids or [])]
    if any(not edge_id for edge_id in exact_support):
        raise ValueError("supporting authority edge ids must be non-empty")
    return service.authority_explain(
        exact_edge_ids,
        starting_ref=starting_ref,
        expected_target_ref=expected_target_ref,
        supporting_edge_ids=exact_support,
    )


def authority_reach_cli(
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
    """Return the canonical product projection for ``authority reach``.

    CLI code must not reinterpret raw authority-engine payloads.  In particular,
    connectivity, material lineage, reliance, and affectedness are not permission
    evidence, unresolved constraints remain blocked, and capability filters only
    select already-recorded authority rather than granting it.
    """
    return authority_reach_product(
        service,
        ref,
        compromise_model=compromise_model,
        capability_filter=capability_filter,
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
    capability_filter: list[tuple[str, str]] | None = None,
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
        capability_filter=capability_filter,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )


__all__ = [
    "AuthorityCliService",
    "authority_blast_cli",
    "authority_explain_cli",
    "authority_reach_cli",
    "authority_subject_cli",
]
