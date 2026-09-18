from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from testamur.assessment import PolicyEngine
from testamur.policy import PolicyStore


class StableEvidence:
    def object_state(self, object_ref: str) -> Mapping[str, Any]:
        if object_ref not in {"claim:root", "claim:dependency"}:
            raise KeyError(object_ref)
        kind = "claim" if object_ref == "claim:root" else "dependency"
        return {"kind": kind, "state": "recorded", "object_ref": object_ref}

    def revision_ref(self, object_ref: str) -> str | None:
        return {"claim:root": "rev:root:1", "claim:dependency": "rev:dependency:1"}[object_ref]

    def assurances_for(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return ()

    def outgoing_relations(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        if object_ref == "claim:root":
            return (
                {
                    "relation_id": "relation:depends-on",
                    "relation_type": "depends_on",
                    "source_ref": "claim:root",
                    "target_ref": "claim:dependency",
                },
            )
        return ()

    def incoming_relations(self, object_ref: str) -> Iterable[Mapping[str, Any]]:
        return ()


def test_gate_e_same_evidence_yields_policy_scoped_explainable_assessments(tmp_path: Path) -> None:
    db = tmp_path / "testamur.sqlite3"
    scope = "project:fixture"
    evidence = StableEvidence()
    policies = PolicyStore(db)

    permissive = policies.register(
        scope_ref=scope,
        purpose="inspect",
        target_kind="claim",
        definition={
            "required_assurances": [],
            "dependency_relation_types": [],
            "blocking_relation_types": [],
            "require_dependencies_admissible": False,
        },
    )
    strict = policies.register(
        scope_ref=scope,
        purpose="build",
        target_kind="claim",
        definition={
            "required_assurances": [],
            "dependency_relation_types": ["depends_on"],
            "blocking_relation_types": [],
            "require_dependencies_admissible": True,
            "allow_unruled_dependencies": False,
        },
    )

    engine = PolicyEngine(policies, evidence)
    inspect = engine.evaluate(scope_ref=scope, object_ref="claim:root", purpose="inspect")
    build = engine.evaluate(scope_ref=scope, object_ref="claim:root", purpose="build")

    assert inspect["policy"]["policy_id"] == permissive["policy_id"]
    assert inspect["admissible"] is True
    assert inspect["blockers"] == []

    assert build["policy"]["policy_id"] == strict["policy_id"]
    assert build["admissible"] is False
    assert any(item["type"] == "dependency_unknown" for item in build["blockers"])
    assert build["dependencies"][0]["state"]["status"] == "unruled"

    assert evidence.revision_ref("claim:root") == "rev:root:1"
    assert evidence.revision_ref("claim:dependency") == "rev:dependency:1"
    assert permissive["content_hash"] != strict["content_hash"]
