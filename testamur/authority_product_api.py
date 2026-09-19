from __future__ import annotations

from typing import Any, Mapping

from .authority_product_projection import project_authority_result


_PRODUCT_SCHEMAS = {
    "testamur.product.authority-reachability.v1",
    "testamur.product.authority-blast-radius.v1",
}


def project_product_authority_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Project a ProductService authority envelope for CLI/Web consumers.

    ProductService owns object lookup/error semantics; the canonical authority
    engine owns reachability semantics.  This adapter deliberately does not
    reinterpret either layer.  In particular, an error envelope stays an error,
    and a successful result is projected without collapsing capability
    constraints or reconstructing evidence from graph connectivity.
    """
    if not bool(envelope.get("ok")):
        return dict(envelope)

    schema = str(envelope.get("schema") or "")
    if schema not in _PRODUCT_SCHEMAS:
        raise ValueError(f"unsupported product authority schema: {schema or '<missing>'}")

    raw_result = envelope.get("result")
    if not isinstance(raw_result, Mapping):
        raise ValueError("product authority envelope result must be a mapping")

    projected = project_authority_result(raw_result)
    return {
        "ok": True,
        "schema": "testamur.product.authority-result.v1",
        "operation_schema": schema,
        "result": projected,
        "semantics": {
            "engine_result_is_authority_source_of_truth": True,
            "connectivity_is_not_authorization": True,
            "lineage_is_not_authority": True,
            "affectedness_does_not_seed_compromise": True,
            "blocked_is_not_partial_authority": True,
            "capability_constraints_are_not_collapsed": True,
        },
    }


__all__ = ["project_product_authority_envelope"]
