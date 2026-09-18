from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from testamur.assessment import PolicyEngine
from testamur.policy import PolicyStore
from testamur.product_service import TestamurProductService
from testamur.reliance import RelianceStore


class MutableEvidence:
    def __init__(self) -> None:
        self.revisions = {
            "tst:record:upstream": "tst:record-revision:upstream-v1",
            "tst:record:downstream": "tst:record-revision:downstream-v1",
        }

    def object_state(self, object_ref: str) -> Mapping[str, Any]:
        if object_ref not in self.revisions:
            raise KeyError(object_ref)
        return {"kind": "claim", "state": "recorded"}

    def revision_ref(self, object_ref: str) -> str | None:
        if object_ref not in self.revisions:
            raise KeyError(object_ref)
        return self.revisions[object_ref]

    def assurances_for(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return ()

    def outgoing_relations(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return ()

    def incoming_relations(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return ()


def test_gate_a_changed_relied_revision_becomes_review_obligation_not_false(tmp_path: Path) -> None:
    db = tmp_path / "testamur.sqlite3"
    scope = "project:fixture"
    purpose = "build"
    evidence = MutableEvidence()
    policies = PolicyStore(db)
    policies.register(
        scope_ref=scope,
        purpose=purpose,
        target_kind="claim",
        definition={
            "required_assurances": [],
            "dependency_relation_types": [],
            "blocking_relation_types": [],
            "require_dependencies_admissible": False,
        },
    )
    engine = PolicyEngine(policies, evidence)
    reliance = RelianceStore(db, engine)
    issued = reliance.issue(
        scope_ref=scope,
        reliant_ref="tst:record:downstream",
        reliant_revision_ref="tst:record-revision:downstream-v1",
        object_ref="tst:record:upstream",
        purpose=purpose,
    )
    assert issued["stale"] is False
    assert issued["pinned_revisions"]["tst:record:upstream"] == "tst:record-revision:upstream-v1"

    evidence.revisions["tst:record:upstream"] = "tst:record-revision:upstream-v2"
    checked = reliance.verify(issued["receipt_id"])
    assert checked["stale"] is True
    assert checked["semantics"]["staleness_requires_reconsideration"] is True
    assert checked["semantics"]["staleness_implies_false"] is False
    assert any(
        reason["type"] == "object_revision_changed"
        and reason["object_ref"] == "tst:record:upstream"
        and reason["was"] == "tst:record-revision:upstream-v1"
        and reason["now"] == "tst:record-revision:upstream-v2"
        for reason in checked["staleness_reasons"]
    )

    product = TestamurProductService.integrated(
        db,
        reliance_store=reliance,
        impact_scope_ref=scope,
    )
    impact = product.impact("tst:record:upstream")
    assert impact["ok"] is True
    assert impact["impact"]["affected_receipt_count"] == 1
    assert impact["impact"]["affected_reliant_refs"] == ["tst:record:downstream"]
    assert impact["impact"]["affected_receipts"][0]["currently_stale"] is True
    assert impact["semantics"]["actual_durable_reliance_only"] is True
    assert impact["semantics"]["change_implies_review"] is True
    assert impact["semantics"]["change_implies_invalid"] is False
    assert impact["semantics"]["stale_implies_false"] is False
