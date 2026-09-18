from __future__ import annotations

import pytest

from testamur.contracts import ObjectKind, classify_object_ref
from testamur.object_projection import (
    BRIDGE_SCHEMA,
    BridgeConflictError,
    ProjectionRelation,
    compare_bridge_envelopes,
    extension_object_id,
    project_legacy_extension,
    reconcile_bridge_envelopes,
)


@pytest.mark.parametrize(
    ("kind", "prefix"),
    [
        (ObjectKind.WORK_SESSION, "tst:work-session:"),
        (ObjectKind.RELIANCE, "tst:reliance:"),
        (ObjectKind.POLICY, "tst:policy:"),
        (ObjectKind.ASSESSMENT, "tst:assessment:"),
        (ObjectKind.LINEAGE, "tst:lineage:"),
        (ObjectKind.AFFECTEDNESS, "tst:affectedness:"),
        (ObjectKind.ADVISORY, "tst:advisory:"),
        (ObjectKind.ATTESTATION, "tst:attestation:"),
    ],
)
def test_extension_ids_are_canonical_and_classifiable(
    kind: ObjectKind, prefix: str
) -> None:
    first = extension_object_id(kind, {"b": 2, "a": 1})
    second = extension_object_id(kind, {"a": 1, "b": 2})

    assert first == second
    assert first.startswith(prefix)
    ref = classify_object_ref(first)
    assert ref.kind is kind
    assert ref.durable is True


def test_extension_identity_rejects_core_object_kind() -> None:
    with pytest.raises(ValueError, match="not a Testamur extension object kind"):
        extension_object_id(ObjectKind.SOURCE, {"locator": "https://example.test"})


def test_extension_identity_requires_nonempty_identity() -> None:
    with pytest.raises(ValueError, match="identity must not be empty"):
        extension_object_id(ObjectKind.RELIANCE, {})


def test_bridge_projection_is_idempotent_and_preserves_provenance() -> None:
    kwargs = {
        "identity": {"legacy_receipt_id": "wtn:reliance:legacy-1", "purpose": "build"},
        "payload": {"purpose": "build", "admission": "admitted"},
        "source_ref": "wtn:reliance:legacy-1",
        "source_schema": "witness.reliance.v1",
        "provenance": {
            "legacy_project": "demo",
            "legacy_revision": 3,
            "migration": "w1",
        },
    }

    first = project_legacy_extension(ObjectKind.RELIANCE, **kwargs)
    second = project_legacy_extension(ObjectKind.RELIANCE, **kwargs)

    assert first.canonical_ref == second.canonical_ref
    assert first.bridge_digest == second.bridge_digest

    encoded = first.to_json()
    assert encoded["schema"] == BRIDGE_SCHEMA
    assert encoded["source"] == {
        "namespace": "witness",
        "ref": "wtn:reliance:legacy-1",
        "schema": "witness.reliance.v1",
    }
    assert encoded["provenance"]["legacy_revision"] == 3
    assert encoded["semantic_guarantees"] == {
        "identity_projection_only": True,
        "verification_promoted": False,
        "truth_promoted": False,
        "authority_promoted": False,
    }
    assert encoded["bridge_digest"].startswith("sha256:")
    assert compare_bridge_envelopes(first, second).relation is ProjectionRelation.IDENTICAL
    assert reconcile_bridge_envelopes(first, second) is first


def test_bridge_projection_changes_when_provenance_changes() -> None:
    first = project_legacy_extension(
        ObjectKind.POLICY,
        identity={"legacy_policy_id": "policy-1"},
        payload={"purpose": "release"},
        source_ref="policy-1",
        provenance={"revision": 1},
    )
    second = project_legacy_extension(
        ObjectKind.POLICY,
        identity={"legacy_policy_id": "policy-1"},
        payload={"purpose": "release"},
        source_ref="policy-1",
        provenance={"revision": 2},
    )

    assert first.canonical_ref == second.canonical_ref
    assert first.bridge_digest != second.bridge_digest
    comparison = compare_bridge_envelopes(first, second)
    assert comparison.relation is ProjectionRelation.SAME_IDENTITY_CHANGED
    assert comparison.changed_fields == ("provenance",)
    with pytest.raises(BridgeConflictError, match="explicit revision"):
        reconcile_bridge_envelopes(first, second)
    assert reconcile_bridge_envelopes(first, second, allow_explicit_revision=True) is second


def test_same_canonical_identity_cannot_silently_change_legacy_origin() -> None:
    identity = {"legacy_policy_id": "policy-1"}
    first = project_legacy_extension(
        ObjectKind.POLICY,
        identity=identity,
        payload={"purpose": "release"},
        source_ref="policy-1",
        source_namespace="witness",
        provenance={"migration": "w1"},
    )
    conflicting = project_legacy_extension(
        ObjectKind.POLICY,
        identity=identity,
        payload={"purpose": "release"},
        source_ref="policy-1-copy",
        source_namespace="legacy-import",
        provenance={"migration": "w1"},
    )

    comparison = compare_bridge_envelopes(first, conflicting)
    assert comparison.relation is ProjectionRelation.ORIGIN_CONFLICT
    assert set(comparison.changed_fields) >= {"source_namespace", "source_ref"}
    with pytest.raises(BridgeConflictError, match="different source origins"):
        reconcile_bridge_envelopes(first, conflicting, allow_explicit_revision=True)


def test_different_canonical_identities_are_not_reconciled() -> None:
    first = project_legacy_extension(
        ObjectKind.POLICY,
        identity={"legacy_policy_id": "policy-1"},
        payload={"purpose": "release"},
        source_ref="policy-1",
        provenance={},
    )
    second = project_legacy_extension(
        ObjectKind.POLICY,
        identity={"legacy_policy_id": "policy-2"},
        payload={"purpose": "release"},
        source_ref="policy-2",
        provenance={},
    )

    comparison = compare_bridge_envelopes(first, second)
    assert comparison.relation is ProjectionRelation.DIFFERENT_IDENTITY
    with pytest.raises(BridgeConflictError, match="different canonical identities"):
        reconcile_bridge_envelopes(first, second)


def test_bridge_ref_kind_mismatch_is_rejected() -> None:
    reliance_ref = extension_object_id(ObjectKind.RELIANCE, {"id": "r1"})
    from testamur.object_projection import BridgeEnvelope

    with pytest.raises(ValueError, match="does not match kind"):
        BridgeEnvelope(
            kind=ObjectKind.POLICY,
            canonical_ref=reliance_ref,
            source_ref="legacy-policy",
            source_namespace="witness",
            payload={},
            provenance={},
        )
