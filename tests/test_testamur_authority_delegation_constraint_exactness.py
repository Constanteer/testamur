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
    return capability_rejection_diagnostics(
        {"capabilities": [child]},
        [parent],
    )


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
    diagnostics = _diagnostics(
        {"connector_installation_locked": False},
        {"connector_installation_locked": False},
    )
    # Exact preservation must not manufacture a rejection by itself.
    assert diagnostics is None
