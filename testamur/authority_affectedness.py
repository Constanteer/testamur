from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .affectedness import AffectednessState
from .authority import AuthorityEvidenceClass, TestamurAuthorityStore


def _required(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must not be empty")
    return text


def _normalize_states(values: Iterable[str | AffectednessState]) -> set[str]:
    result: set[str] = set()
    for value in values:
        try:
            result.add(AffectednessState(str(value)).value)
        except ValueError as exc:
            raise ValueError(f"unsupported affectedness state in compromise policy: {value!r}") from exc
    if not result:
        raise ValueError("eligible_states must not be empty")
    return result


def _normalize_basis(values: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw in values or ():
        if not isinstance(raw, Mapping):
            raise ValueError("compromise basis entries must be mappings")
        item = dict(raw)
        item["kind"] = _required(item.get("kind"), field="compromise_basis.kind")
        item["ref"] = _required(item.get("ref"), field="compromise_basis.ref")
        evidence_class = item.get("evidence_class")
        if evidence_class is not None:
            try:
                item["evidence_class"] = AuthorityEvidenceClass(str(evidence_class)).value
            except ValueError as exc:
                raise ValueError(
                    "compromise_basis.evidence_class must be OBSERVED, DERIVED, or DECLARED"
                ) from exc
            if item["evidence_class"] == AuthorityEvidenceClass.DERIVED.value:
                item["analyzer"] = _required(
                    item.get("analyzer"), field="compromise_basis.analyzer"
                )
                item["analyzer_version"] = _required(
                    item.get("analyzer_version"),
                    field="compromise_basis.analyzer_version",
                )
        result.append(item)
    return result


def affectedness_compromise_seeds(
    authority: TestamurAuthorityStore,
    assessments: Sequence[Mapping[str, Any]],
    bindings: Sequence[Mapping[str, Any]],
    *,
    policy_ref: str,
    eligible_states: Iterable[str | AffectednessState],
    required_basis_kinds: Iterable[str] = (),
    allow_declared_only_basis: bool = False,
) -> dict[str, Any]:
    """Select explicit authority compromise seeds from affectedness assessments.

    Affectedness never becomes compromise by itself. The caller must provide:
    - an explicit policy reference;
    - eligible affectedness states;
    - an exact subject_revision -> authority_subject_ref binding;
    - explicit compromise basis for each binding.

    The function is intentionally pure: it records no new affectedness or authority
    fact and does not mutate either graph.
    """

    policy = _required(policy_ref, field="policy_ref")
    states = _normalize_states(eligible_states)
    required_kinds = {
        _required(kind, field="required_basis_kinds[]")
        for kind in required_basis_kinds
    }

    assessment_by_subject: dict[str, list[dict[str, Any]]] = {}
    for raw in assessments:
        if not isinstance(raw, Mapping):
            raise ValueError("assessments must contain mappings")
        assessment = dict(raw)
        subject_revision = _required(
            assessment.get("subject_revision"), field="assessment.subject_revision"
        )
        state = _required(assessment.get("state"), field="assessment.state")
        try:
            normalized_state = AffectednessState(state).value
        except ValueError as exc:
            raise ValueError(f"unsupported assessment state {state!r}") from exc
        assessment["state"] = normalized_state
        assessment["assessment_id"] = _required(
            assessment.get("assessment_id"), field="assessment.assessment_id"
        )
        assessment_by_subject.setdefault(subject_revision, []).append(assessment)

    seeds: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for raw in bindings:
        if not isinstance(raw, Mapping):
            raise ValueError("bindings must contain mappings")
        binding = dict(raw)
        subject_revision = _required(
            binding.get("subject_revision"), field="binding.subject_revision"
        )
        authority_subject_ref = _required(
            binding.get("authority_subject_ref"),
            field="binding.authority_subject_ref",
        )
        binding_ref = _required(
            binding.get("binding_ref"), field="binding.binding_ref"
        )
        compromise_basis = _normalize_basis(binding.get("compromise_basis"))

        authority_subject = authority.maybe_subject(authority_subject_ref)
        if authority_subject is None:
            rejected.append(
                {
                    "subject_revision": subject_revision,
                    "authority_subject_ref": authority_subject_ref,
                    "binding_ref": binding_ref,
                    "reasons": ["authority_subject_not_recorded"],
                }
            )
            continue

        candidates = assessment_by_subject.get(subject_revision, [])
        if not candidates:
            rejected.append(
                {
                    "subject_revision": subject_revision,
                    "authority_subject_ref": authority_subject_ref,
                    "binding_ref": binding_ref,
                    "reasons": ["no_affectedness_assessment_for_bound_revision"],
                }
            )
            continue

        eligible = [
            assessment
            for assessment in candidates
            if str(assessment["state"]) in states
        ]
        if not eligible:
            rejected.append(
                {
                    "subject_revision": subject_revision,
                    "authority_subject_ref": authority_subject_ref,
                    "binding_ref": binding_ref,
                    "assessment_ids": sorted(
                        str(item["assessment_id"]) for item in candidates
                    ),
                    "reasons": ["affectedness_state_not_eligible_under_policy"],
                }
            )
            continue

        present_kinds = {
            str(item["kind"]) for item in compromise_basis
        }
        missing_kinds = sorted(required_kinds - present_kinds)
        if missing_kinds:
            rejected.append(
                {
                    "subject_revision": subject_revision,
                    "authority_subject_ref": authority_subject_ref,
                    "binding_ref": binding_ref,
                    "assessment_ids": sorted(
                        str(item["assessment_id"]) for item in eligible
                    ),
                    "reasons": ["required_compromise_basis_missing"],
                    "missing_basis_kinds": missing_kinds,
                }
            )
            continue

        if not compromise_basis:
            rejected.append(
                {
                    "subject_revision": subject_revision,
                    "authority_subject_ref": authority_subject_ref,
                    "binding_ref": binding_ref,
                    "assessment_ids": sorted(
                        str(item["assessment_id"]) for item in eligible
                    ),
                    "reasons": ["compromise_basis_required"],
                }
            )
            continue

        declared_only = all(
            str(item.get("evidence_class") or AuthorityEvidenceClass.DECLARED.value)
            == AuthorityEvidenceClass.DECLARED.value
            for item in compromise_basis
        )
        if declared_only and not allow_declared_only_basis:
            rejected.append(
                {
                    "subject_revision": subject_revision,
                    "authority_subject_ref": authority_subject_ref,
                    "binding_ref": binding_ref,
                    "assessment_ids": sorted(
                        str(item["assessment_id"]) for item in eligible
                    ),
                    "reasons": ["declared_only_compromise_basis_not_accepted"],
                }
            )
            continue

        seeds.append(
            {
                "authority_subject_ref": authority_subject_ref,
                "authority_subject_kind": authority_subject["kind"],
                "subject_revision": subject_revision,
                "binding_ref": binding_ref,
                "policy_ref": policy,
                "assessment_ids": sorted(
                    str(item["assessment_id"]) for item in eligible
                ),
                "affectedness_states": sorted(
                    {str(item["state"]) for item in eligible}
                ),
                "compromise_basis": compromise_basis,
                "declared_only_compromise_basis": declared_only,
            }
        )

    seeds.sort(
        key=lambda item: (
            str(item["authority_subject_ref"]),
            str(item["subject_revision"]),
            str(item["binding_ref"]),
        )
    )
    rejected.sort(
        key=lambda item: (
            str(item.get("authority_subject_ref") or ""),
            str(item.get("subject_revision") or ""),
            str(item.get("binding_ref") or ""),
        )
    )

    return {
        "schema_version": "testamur.affectedness-authority-bridge.v1",
        "policy_ref": policy,
        "eligible_states": sorted(states),
        "required_basis_kinds": sorted(required_kinds),
        "seeds": seeds,
        "seed_refs": sorted({str(item["authority_subject_ref"]) for item in seeds}),
        "rejected": rejected,
        "semantics": {
            "affectedness_alone_never_seeds_compromise": True,
            "revision_to_authority_binding_is_explicit": True,
            "compromise_basis_is_required": True,
            "declared_only_basis_is_not_accepted_by_default": True,
            "policy_selection_is_explicit": True,
        },
    }


__all__ = ["affectedness_compromise_seeds"]
