from testamur.authority_capability import capability_allowed, capability_is_attenuation
from testamur.authority_reachability_policy import capability_rejection_diagnostics


def _capability(constraints):
    return {
        "namespace": "github",
        "action": "contents:read",
        "constraints": constraints,
    }


def _diagnostics(parent_constraints, child_constraints):
    parent = _capability(parent_constraints)
    child = _capability(child_constraints)
    return capability_rejection_diagnostics({"capabilities": [child]}, [parent])


def test_explicit_null_scope_does_not_collapse_to_absence():
    diagnostics = _diagnostics({"scope": None}, {"scope": "repo:read"})
    assert diagnostics is not None
    assert "scope_evidence_malformed" in diagnostics["reasons"]
    assert "scope" in diagnostics["unresolved_constraints"]


def test_typed_gate_evidence_fails_closed():
    diagnostics = _diagnostics({"mfa_required": "true"}, {"mfa_required": True})
    assert diagnostics is not None
    assert "mfa_required_evidence_malformed" in diagnostics["reasons"]
    assert "mfa_required" in diagnostics["unresolved_constraints"]


def test_child_typed_gate_evidence_cannot_preserve_parent_gate():
    diagnostics = _diagnostics({"approval_required": True}, {"approval_required": 1})
    assert diagnostics is not None
    assert "approval_required_evidence_malformed" in diagnostics["reasons"]
    assert "approval_required" in diagnostics["unresolved_constraints"]


def test_falsey_provider_constraint_must_be_preserved_exactly():
    diagnostics = _diagnostics({"connector_installation_locked": False}, {})
    assert diagnostics is not None
    assert "provider_constraint_mismatch" in diagnostics["reasons"]
    assert "connector_installation_locked" in diagnostics["failed_constraints"]


def test_falsey_provider_constraint_can_be_preserved_exactly():
    diagnostics = _diagnostics({"connector_installation_locked": False}, {"connector_installation_locked": False})
    assert diagnostics is None


def test_explicit_null_parent_expiry_is_malformed_not_absent():
    diagnostics = _diagnostics({"expires_at": None}, {"expires_at": "2026-09-24T10:00:00Z"})
    assert diagnostics is not None
    assert "expiry_evidence_malformed" in diagnostics["reasons"]
    assert "expires_at" in diagnostics["unresolved_constraints"]


def test_parent_expiry_must_be_preserved_by_child():
    diagnostics = _diagnostics({"expires_at": "2026-09-24T10:00:00Z"}, {})
    assert diagnostics is not None
    assert "expiry_not_preserved" in diagnostics["reasons"]
    assert "expires_at" in diagnostics["failed_constraints"]


def test_child_expiry_cannot_extend_parent_delegation():
    diagnostics = _diagnostics({"expires_at": "2026-09-24T10:00:00Z"}, {"expires_at": "2026-09-24T11:00:00Z"})
    assert diagnostics is not None
    assert "expiry_outside_delegation" in diagnostics["reasons"]


def test_child_may_narrow_parent_expiry():
    diagnostics = _diagnostics({"expires_at": "2026-09-24T10:00:00Z"}, {"expires_at": "2026-09-24T09:00:00Z"})
    assert diagnostics is None


def test_explicit_null_repository_selection_is_not_absence():
    malformed = _capability({"repository_selection": None})
    assert capability_allowed(malformed, None) is False
    diagnostics = _diagnostics({"repository_selection": None}, {"repository_selection": "all"})
    assert diagnostics is not None
    assert "repository_selection_evidence_malformed" in diagnostics["reasons"]
    assert "repository_selection" in diagnostics["unresolved_constraints"]


def test_typed_repository_selection_is_not_stringified():
    malformed = _capability({"repository_selection": {"mode": "all"}})
    assert capability_allowed(malformed, None) is False
    diagnostics = _diagnostics({"repository_selection": "all"}, {"repository_selection": {"mode": "selected"}})
    assert diagnostics is not None
    assert "repository_selection_evidence_malformed" in diagnostics["reasons"]


def test_selected_repository_scope_requires_exact_refs():
    malformed = _capability({"repository_selection": "selected"})
    assert capability_allowed(malformed, None) is False
    diagnostics = _diagnostics({"repository_selection": "selected"}, {"repository_selection": "selected", "repository_ref": "repo:one"})
    assert diagnostics is not None
    assert "repository_selection_evidence_malformed" in diagnostics["reasons"]


def test_all_repository_scope_rejects_stray_refs_as_malformed_evidence():
    diagnostics = _diagnostics(
        {"repository_selection": "all", "repository_ref": "repo:one"},
        {"repository_selection": "selected", "repository_ref": "repo:one"},
    )
    assert diagnostics is not None
    assert "repository_selection_evidence_malformed" in diagnostics["reasons"]
    assert "repository_selection" in diagnostics["unresolved_constraints"]


def test_selected_repository_scope_may_narrow_all_parent():
    parent = _capability({"repository_selection": "all"})
    child = _capability({"repository_selection": "selected", "repository_ref": "repo:one"})
    assert capability_is_attenuation(child, parent) is True


def test_falsey_provider_constraint_cannot_disappear_in_canonical_attenuation():
    parent = _capability({"connector_installation_locked": False})
    child = _capability({})
    assert capability_is_attenuation(child, parent) is False


def test_explicit_null_constraints_container_is_malformed():
    malformed = {"namespace": "github", "action": "contents:read", "constraints": None}
    assert capability_allowed(malformed, None) is False


def test_typed_constraint_identity_is_malformed():
    malformed = {"namespace": "github", "action": "contents:read", "constraints": {7: False}}
    assert capability_allowed(malformed, None) is False
