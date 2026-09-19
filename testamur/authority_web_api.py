from __future__ import annotations

from typing import Any, Mapping, Protocol
from urllib.parse import parse_qs, urlsplit

from .authority_product_service import AuthorityProductService
from .authority_web_service import authority_blast_web, authority_reach_web


_SUBJECT_PATH = "/v1/authority/subject"
_EXPLAIN_PATH = "/v1/authority/explain"
_REACH_PATH = "/v1/authority/reach"
_BLAST_PATH = "/v1/authority/blast-radius"
_REACH_ALLOWED = {"ref", "compromise_model", "max_depth", "max_paths", "expansion_budget", "as_of"}
_SUBJECT_ALLOWED = {"ref"}
_EXPLAIN_ALLOWED = {"edge_id", "support_edge_id", "start", "target"}


class AuthorityWebService(AuthorityProductService, Protocol):
    """Authority reads required by the Web API.

    Subject/path inspection is deliberately exact-edge based.  The Web layer is
    not permitted to manufacture an authority path from adjacency, material
    lineage, reliance, or affectedness.
    """

    def authority_subject(self, ref: str) -> dict[str, Any]: ...

    def authority_explain(
        self,
        edge_ids: list[str],
        *,
        starting_ref: str | None = None,
        expected_target_ref: str | None = None,
        supporting_edge_ids: list[str] | None = None,
    ) -> dict[str, Any]: ...


def _one(query: Mapping[str, list[str]], name: str, *, required: bool = True) -> str | None:
    values = query.get(name) or []
    if not values:
        if required:
            raise ValueError(f"missing required query parameter: {name}")
        return None
    if len(values) != 1 or not values[0].strip():
        raise ValueError(f"query parameter {name} must occur exactly once and be non-empty")
    return values[0].strip()


def _exact_list(query: Mapping[str, list[str]], name: str, *, required: bool = False) -> list[str]:
    raw = query.get(name) or []
    values = [value.strip() for value in raw if value.strip()]
    if len(values) != len(raw):
        raise ValueError(f"query parameter {name} values must be non-empty")
    if required and not values:
        raise ValueError(f"at least one {name} query parameter is required")
    return values


def _positive_int(query: Mapping[str, list[str]], name: str, default: int, maximum: int) -> int:
    raw = _one(query, name, required=False)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < 1 or value > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return value


def _reject_unknown(query: Mapping[str, list[str]], allowed: set[str]) -> None:
    unknown = set(query) - allowed
    if unknown:
        raise ValueError(f"authority route does not accept query parameters: {', '.join(sorted(unknown))}")


def dispatch_authority_web_api(service: AuthorityWebService, target: str) -> dict[str, Any] | None:
    """Dispatch authority-only Web API reads without reinterpreting graph semantics.

    Returns ``None`` when ``target`` is not an authority route so the outer Web
    router can continue normal dispatch. Reach/blast successful payloads come
    exclusively from the canonical authority engine -> Product projection -> Web
    projection chain. Subject and explanation reads expose only canonical stored
    authority objects and exact edge paths. Connectivity, lineage, reliance, or
    affectedness are never accepted as substitutes for explicit authority evidence.
    """
    split = urlsplit(target)
    path = split.path.rstrip("/") or "/"
    if path not in {_SUBJECT_PATH, _EXPLAIN_PATH, _REACH_PATH, _BLAST_PATH}:
        return None

    query = parse_qs(split.query, keep_blank_values=True)

    if path == _SUBJECT_PATH:
        _reject_unknown(query, _SUBJECT_ALLOWED)
        return service.authority_subject(_one(query, "ref") or "")

    if path == _EXPLAIN_PATH:
        _reject_unknown(query, _EXPLAIN_ALLOWED)
        edge_ids = _exact_list(query, "edge_id", required=True)
        supporting_edge_ids = _exact_list(query, "support_edge_id")
        return service.authority_explain(
            edge_ids,
            starting_ref=_one(query, "start", required=False),
            expected_target_ref=_one(query, "target", required=False),
            supporting_edge_ids=supporting_edge_ids,
        )

    _reject_unknown(query, _REACH_ALLOWED)
    compromise_model = _one(query, "compromise_model") or ""
    max_depth = _positive_int(query, "max_depth", 8, 64)
    max_paths = _positive_int(query, "max_paths", 256, 4096)
    expansion_budget = _positive_int(query, "expansion_budget", 10000, 1000000)
    as_of = _one(query, "as_of", required=False)

    refs = _exact_list(query, "ref", required=True)
    if path == _REACH_PATH:
        if len(refs) != 1:
            raise ValueError("authority reach requires exactly one non-empty ref")
        return authority_reach_web(
            service,
            refs[0],
            compromise_model=compromise_model,
            max_depth=max_depth,
            max_paths=max_paths,
            expansion_budget=expansion_budget,
            as_of=as_of,
        )

    return authority_blast_web(
        service,
        refs,
        compromise_model=compromise_model,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )


__all__ = ["AuthorityWebService", "dispatch_authority_web_api"]
