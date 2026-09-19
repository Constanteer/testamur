from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from .authority_product_service import AuthorityProductService
from .authority_web_service import authority_blast_web, authority_reach_web


_REACH_PATH = "/v1/authority/reach"
_BLAST_PATH = "/v1/authority/blast-radius"
_ALLOWED = {"ref", "compromise_model", "max_depth", "max_paths", "expansion_budget", "as_of"}


def _one(query: Mapping[str, list[str]], name: str, *, required: bool = True) -> str | None:
    values = query.get(name) or []
    if not values:
        if required:
            raise ValueError(f"missing required query parameter: {name}")
        return None
    if len(values) != 1 or not values[0].strip():
        raise ValueError(f"query parameter {name} must occur exactly once and be non-empty")
    return values[0].strip()


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


def dispatch_authority_web_api(service: AuthorityProductService, target: str) -> dict[str, Any] | None:
    """Dispatch authority-only Web API reads without reinterpreting graph semantics.

    Returns ``None`` when ``target`` is not an authority route so the outer Web
    router can continue normal dispatch.  Successful payloads come exclusively
    from the canonical authority engine -> Product projection -> Web projection
    chain.  Query connectivity, lineage, reliance, or affectedness are never
    accepted as substitutes for explicit compromise seeds or authority evidence.
    """
    split = urlsplit(target)
    path = split.path.rstrip("/") or "/"
    if path not in {_REACH_PATH, _BLAST_PATH}:
        return None

    query = parse_qs(split.query, keep_blank_values=True)
    unknown = set(query) - _ALLOWED
    if unknown:
        raise ValueError(f"authority route does not accept query parameters: {', '.join(sorted(unknown))}")

    compromise_model = _one(query, "compromise_model") or ""
    max_depth = _positive_int(query, "max_depth", 8, 64)
    max_paths = _positive_int(query, "max_paths", 256, 4096)
    expansion_budget = _positive_int(query, "expansion_budget", 10000, 1000000)
    as_of = _one(query, "as_of", required=False)

    refs = [value.strip() for value in query.get("ref") or [] if value.strip()]
    if not refs:
        raise ValueError("missing required query parameter: ref")

    if path == _REACH_PATH:
        if len(refs) != 1 or len(query.get("ref") or []) != 1:
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

    if len(refs) != len(query.get("ref") or []):
        raise ValueError("authority blast-radius refs must be non-empty")
    return authority_blast_web(
        service,
        refs,
        compromise_model=compromise_model,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )


__all__ = ["dispatch_authority_web_api"]
