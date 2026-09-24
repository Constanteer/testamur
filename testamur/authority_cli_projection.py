from __future__ import annotations

from typing import Any, Protocol

from .authority_exact import exact_nonempty_string
from .authority_filter import normalize_capability_filter
from .authority_product_service import (
    AuthorityProductService,
    authority_blast_product,
    authority_reach_product,
)
from .authority_seed import exact_subject_ref, normalize_compromise_seeds


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


def _exact_optional_ref(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    return exact_nonempty_string(value, field=field)


def _exact_edge_ids(values: Any, *, field: str, allow_empty: bool = False) -> list[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValueError(f"{field} must be a sequence of exact edge ids")
    result = [exact_nonempty_string(value, field=f"{field}[]") for value in values]
    if not allow_empty and not result:
        raise ValueError(f"{field} requires at least one exact edge id")
    return result


def authority_subject_cli(service: AuthorityCliService, ref: str) -> dict[str, Any]:
    """Inspect one canonical authority subject and its exact recorded edges.

    This is intentionally a pass-through read. The CLI must not turn adjacency,
    material lineage, reliance, or affectedness into permission evidence.
    """
    return service.authority_subject(exact_subject_ref(ref, field="authority_subject.ref"))


def authority_explain_cli(
    service: AuthorityCliService,
    edge_ids: list[str],
    *,
    starting_ref: str | None = None,
    expected_target_ref: str | None = None,
    supporting_edge_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Explain an explicit ordered authority path plus separate support evidence."""
    return service.authority_explain(
        _exact_edge_ids(edge_ids, field="authority_explain.edge_ids"),
        starting_ref=_exact_optional_ref(starting_ref, field="authority_explain.starting_ref"),
        expected_target_ref=_exact_optional_ref(
            expected_target_ref, field="authority_explain.expected_target_ref"
        ),
        supporting_edge_ids=_exact_edge_ids(
            supporting_edge_ids or [],
            field="authority_explain.supporting_edge_ids",
            allow_empty=True,
        ),
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

    CLI code must not reinterpret raw authority-engine payloads. In particular,
    connectivity, material lineage, reliance, and affectedness are not permission
    evidence, unresolved constraints remain blocked, and capability filters only
    select already-recorded authority rather than granting it.
    """
    return authority_reach_product(
        service,
        exact_subject_ref(ref, field="authority_reach.ref"),
        compromise_model=exact_nonempty_string(
            compromise_model, field="authority_reach.compromise_model"
        ),
        capability_filter=normalize_capability_filter(capability_filter),
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
        normalize_compromise_seeds(refs),
        compromise_model=exact_nonempty_string(
            compromise_model, field="authority_blast.compromise_model"
        ),
        capability_filter=normalize_capability_filter(capability_filter),
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
