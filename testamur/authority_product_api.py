from __future__ import annotations

from typing import Any, Mapping

from .authority_product_projection import project_authority_result
from .authority_projection import project_authority_decision


_PRODUCT_SCHEMAS = {
    "testamur.product.authority-reachability.v1",
    "testamur.product.authority-blast-radius.v1",
}


def project_product_authority_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Project a ProductService authority envelope for CLI/Web consumers.

    ProductService owns object lookup/error semantics; the canonical authority
    engine owns reachability semantics. This adapter deliberately does not
    reinterpret either layer. In particular, an error envelope stays an error,
    and a successful result is projected without collapsing capability
    constraints or reconstructing evidence from graph connectivity.

    ``decision`` is a presentation/explanation projection of the same canonical
    engine result. It is never additional authority evidence and therefore may
    not be used to manufacture grants, credential acceptance, or compromise
    seeds that were absent from ``result``.
    """
    if not bool(envelope.get("ok")):
        return dict(envelope)

    schema = envelope.get("schema")
    if not isinstance(schema, str) or not schema.strip():
        raise ValueError("product authority envelope schema must be an exact non-empty string")
    if schema not in _PRODUCT_SCHEMAS:
        raise ValueError(f"unsupported product authority schema: {schema}")

    raw_result = envelope.get("result")
    if not isinstance(raw_result, Mapping):
        raise ValueError("product authority envelope result must be a mapping")

    projected = project_authority_result(raw_result)
    decision = project_authority_decision(raw_result)
    return {
        "ok": True,
        "schema": "testamur.product.authority-result.v1",
        "operation_schema": schema,
        "result": projected,
        "decision": decision,
        "semantics": {
            "engine_result_is_authority_source_of_truth": True,
            "decision_projection_is_not_authority_evidence": True,
            "supporting_acceptance_edges_do_not_expand_authority": True,
            "delegated_capability_budget_remains_attenuating": True,
            "connectivity_is_not_authorization": True,
            "lineage_is_not_authority": True,
            "affectedness_does_not_seed_compromise": True,
            "blocked_is_not_partial_authority": True,
            "capability_constraints_are_not_collapsed": True,
        },
    }


__all__ = ["project_product_authority_envelope"]
