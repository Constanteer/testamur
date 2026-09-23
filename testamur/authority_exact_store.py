from __future__ import annotations

from typing import Any, Mapping

from .authority_edge_identity import exact_authority_edge_identity, exact_optional_constraint_ref
from .authority_seed import exact_subject_ref


class ExactAuthorityStoreView:
    """Fail-closed view over the authority store used by reachability engines.

    The raw traversal engine historically normalizes several identity-bearing fields
    with ``str(...)``. This view validates records *before* they reach that code so
    malformed typed evidence cannot become a subject, edge, relation, service,
    credential identity, trust-boundary annotation, subject kind, or provenance
    class merely because it is connected in the graph.

    This is deliberately not a material-lineage adapter: it only preserves and
    validates authority records already returned by the authority store.
    """

    def __init__(self, store: Any):
        self._store = store

    @staticmethod
    def _validate_edge(edge: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(edge, Mapping):
            raise ValueError("authority edge must be a mapping")
        exact_authority_edge_identity(edge)
        constraints = edge.get("constraints")
        if constraints is not None and not isinstance(constraints, Mapping):
            raise ValueError("authority edge constraints must be a mapping when present")
        if isinstance(constraints, Mapping) and "service_ref" in constraints:
            exact_optional_constraint_ref(constraints.get("service_ref"), field="constraints.service_ref")

        boundary_refs = edge.get("boundary_refs")
        if boundary_refs is not None:
            if isinstance(boundary_refs, (str, bytes, bytearray)) or not isinstance(boundary_refs, (list, tuple)):
                raise ValueError("authority edge boundary_refs must be a sequence of exact refs when present")
            for index, boundary_ref in enumerate(boundary_refs):
                exact_optional_constraint_ref(
                    boundary_ref,
                    field=f"authority edge boundary_refs[{index}]",
                )

        evidence = edge.get("evidence")
        if evidence is not None:
            if isinstance(evidence, (str, bytes, bytearray)) or not isinstance(evidence, (list, tuple)):
                raise ValueError("authority edge evidence must be a sequence of mappings when present")
            for index, item in enumerate(evidence):
                if not isinstance(item, Mapping):
                    raise ValueError(f"authority edge evidence[{index}] must be a mapping")
                if "evidence_class" in item:
                    value = item.get("evidence_class")
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"authority edge evidence[{index}].evidence_class must be an exact non-empty string")
        return edge

    @staticmethod
    def _validate_subject(subject: Any) -> Mapping[str, Any] | None:
        if subject is None:
            return None
        if not isinstance(subject, Mapping):
            raise ValueError("authority subject must be a mapping")
        if "subject_ref" in subject:
            exact_subject_ref(subject.get("subject_ref"), field="authority subject subject_ref")
        if "kind" in subject:
            kind = subject.get("kind")
            if not isinstance(kind, str) or not kind.strip():
                raise ValueError("authority subject kind must be an exact non-empty string")
        attributes = subject.get("attributes")
        if attributes is not None and not isinstance(attributes, Mapping):
            raise ValueError("authority subject attributes must be a mapping when present")
        return subject

    def edges_from(self, source_ref: str):
        exact_subject_ref(source_ref, field="edges_from source_ref")
        return [self._validate_edge(edge) for edge in self._store.edges_from(source_ref)]

    def list_edges(self, *args, **kwargs):
        for field in ("source_ref", "target_ref"):
            if field in kwargs and kwargs[field] is not None:
                exact_subject_ref(kwargs[field], field=f"list_edges {field}")
        return [self._validate_edge(edge) for edge in self._store.list_edges(*args, **kwargs)]

    def get_edge(self, edge_id: str):
        if not isinstance(edge_id, str) or not edge_id.strip():
            raise ValueError("get_edge edge_id must be an exact non-empty string")
        return self._validate_edge(self._store.get_edge(edge_id))

    def maybe_subject(self, subject_ref: str):
        exact_subject_ref(subject_ref, field="maybe_subject subject_ref")
        return self._validate_subject(self._store.maybe_subject(subject_ref))

    def get_subject(self, subject_ref: str):
        exact_subject_ref(subject_ref, field="get_subject subject_ref")
        return self._validate_subject(self._store.get_subject(subject_ref))

    def __getattr__(self, name: str):
        return getattr(self._store, name)


__all__ = ["ExactAuthorityStoreView"]
