from datetime import datetime, timezone

from testamur.authority_reachability_policy import capability_rejection_diagnostics


def _edge(constraints):
    return {
        "capabilities": [
            {
                "namespace": "github",
                "action": "contents.write",
                "resource": "repo:one",
                "constraints": constraints,
            }
        ]
    }


def _budget(constraints):
    return [
        {
            "namespace": "github",
            "action": "contents.write",
            "resource": "repo:one",
            "constraints": constraints,
        }
    ]


def test_diagnostics_do_not_stringify_typed_scope_evidence():
    result = capability_rejection_diagnostics(
        _edge({"scope": "contents:write"}),
        _budget({"scopes": [123]}),
    )

    assert result is not None
    assert "scope_evidence_malformed" in result["reasons"]
    assert "scope" in result["failed_constraints"]
    assert "scope" in result["unresolved_constraints"]


def test_diagnostics_do_not_assume_timezone_for_typed_or_naive_expiry():
    typed = capability_rejection_diagnostics(
        _edge({"expires_at": "2026-09-23T12:00:00Z"}),
        _budget({"expires_at": datetime(2026, 9, 23, 13, 0, tzinfo=timezone.utc)}),
    )
    naive = capability_rejection_diagnostics(
        _edge({"expires_at": "2026-09-23T12:00:00Z"}),
        _budget({"expires_at": "2026-09-23T13:00:00"}),
    )

    for result in (typed, naive):
        assert result is not None
        assert "expiry_evidence_malformed" in result["reasons"]
        assert "expires_at" in result["failed_constraints"]
        assert "expires_at" in result["unresolved_constraints"]


def test_diagnostics_do_not_stringify_malformed_capability_identity():
    result = capability_rejection_diagnostics(
        {
            "capabilities": [
                {
                    "namespace": 7,
                    "action": "contents.write",
                    "resource": "repo:one",
                    "constraints": {},
                }
            ]
        },
        _budget({}),
    )

    assert result is not None
    assert "delegated_capability_identity_mismatch" in result["reasons"]
    assert {"namespace", "action"} <= set(result["failed_constraints"])
    assert {"namespace", "action"} <= set(result["unresolved_constraints"])


def test_diagnostics_do_not_stringify_resource_pattern_evidence():
    result = capability_rejection_diagnostics(
        _edge({"resource_pattern": "repo:*"}),
        _budget({"resource_pattern": 123}),
    )

    assert result is not None
    assert "resource_pattern_evidence_malformed" in result["reasons"]
    assert "resource_pattern" in result["unresolved_constraints"]
