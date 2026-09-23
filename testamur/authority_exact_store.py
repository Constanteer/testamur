from __future__ import annotations

from typing import Any, Mapping

from .authority_edge_identity import exact_authority_edge_identity, exact_optional_constraint_ref


class ExactAuthorityStoreView:
    """Fail-closed view over the authority store used by reachability engines.

    The raw traversal engine historically normalizes several identity-bearing fields
    with ``str(...)``.  This view validates records *before* they reach that code so
    malformed typed evidence cannot become a subject, edge, relation, service, or
    credential identity merely because it is connected in the graph.

    This is deliberately not a material-lineage adapter: it only preserves and
    validates authority records already returned by the authority store.
    """

    def __init__(self, store: Any):
        self._store = store

    @staticmethod
    def _validate_edge(edge: Mapping[str, Any]) -> Mapping[str, Any]:
        exact_authority_edge_identity(edge)
        constraints = edge.get("constraints")
        if constraints is not None and not isinstance(constraints, Mapping):
            raise ValueError("authority edge constraints must be a mapping when present")
        if isinstance(constraints, Mapping) and "service_ref" in constraints:
            exact_optional_constraint_ref(constraints.get("service_ref"), field="constraints.service_ref")
        return edge

    def edges_from(self, source_ref: str):
        return [self._validate_edge(edge) for edge in self._store.edges_from(source_ref)]

    def list_edges(self, *args, **kwargs):
        return [self._validate_edge(edge) for edge in self._store.list_edges(*args, **kwargs)]

    def get_edge(self, edge_id: str):
        return self._validate_edge(self._store.get_edge(edge_id))

    def __getattr__(self, name: str):
        return getattr(self._store, name)


__all__ = ["ExactAuthorityStoreView"]
