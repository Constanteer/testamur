from __future__ import annotations

from typing import Any, Mapping

from . import source_gateway_mcp as _base
from .advisory_write_route import record_advisory_assessment


PROJECT_REVALIDATION_TOOL = {
    "name": "testamur.project_advisory_revalidation",
    "title": "Inspect Project advisory revalidation work",
    "description": (
        "Return the canonical advisory revalidation work projection for an existing Project. "
        "Dependency change is a review trigger, not an invalidity or affectedness verdict; "
        "recorded assessments are not generic verification."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {"project_ref": {"type": "string"}},
        "required": ["project_ref"],
        "additionalProperties": False,
    },
}

ADVISORY_ASSESSMENT_TOOL = {
    "name": "testamur.record_advisory_assessment",
    "title": "Record advisory affectedness evidence",
    "description": (
        "Record evidence and provenance for one immutable advisory revision through the canonical "
        "affectedness engine. The caller cannot supply a verdict/state/trust score; recording evidence "
        "is not verification, reliance, or an affectedness verdict by itself."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "event_revision_id": {"type": "string"},
            "subject_revision": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "object"}},
            "basis": {"type": "array", "items": {"type": "object"}},
            "scope": {"type": "object"},
            "lineage_path_edge_ids": {"type": "array", "items": {"type": "string"}},
            "analyzer": {"type": "object"},
            "policy_ref": {"type": "string"},
            "supersedes_assessment_id": {"type": "string"},
        },
        "required": ["event_revision_id", "subject_revision", "evidence", "basis"],
        "additionalProperties": False,
    },
}


def _project_revalidation(arguments: Mapping[str, Any]) -> dict[str, Any]:
    service = _base.TestamurProductService.integrated(_base._db_path())
    project_ref = _base._required(arguments, "project_ref")
    detail = _base.project_with_advisory_reviews(service, project_ref)
    if detail.get("ok") is not True:
        return detail
    supply = detail.get("supply_chain")
    if not isinstance(supply, Mapping):
        supply = {}
    projection = supply.get("advisory_revalidation")
    if not isinstance(projection, Mapping):
        projection = {}
    return {
        "ok": True,
        "schema": "testamur.mcp.project-advisory-revalidation.v1",
        "project": detail["project"],
        "advisory_revalidation": dict(projection),
        "semantics": {
            "changed_is_not_invalid": True,
            "changed_is_not_affectedness_verdict": True,
            "stale_is_not_false": True,
            "candidate_overlap_is_not_affectedness_verdict": True,
            "recorded_assessment_is_not_generic_verification": True,
            "generic_trust_score_used": False,
        },
    }


def _record_advisory_assessment(arguments: Mapping[str, Any]) -> dict[str, Any]:
    service = _base.TestamurProductService.integrated(_base._db_path())
    result = record_advisory_assessment(service, arguments)
    return {
        "ok": True,
        "schema": "testamur.mcp.advisory-assessment.v1",
        "assessment": result,
        "semantics": {
            "recorded_is_not_verified": True,
            "recorded_is_not_relied": True,
            "lineage_is_not_affectedness_verdict": True,
            "caller_supplies_verdict": False,
            "generic_trust_score_used": False,
        },
    }


def _install() -> None:
    for tool in (PROJECT_REVALIDATION_TOOL, ADVISORY_ASSESSMENT_TOOL):
        if not any(existing.get("name") == tool["name"] for existing in _base.TOOLS):
            _base.TOOLS.append(tool)
    base_call = _base._call_tool
    if getattr(base_call, "_testamur_project_extension", False):
        return

    def call_tool(name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if name == PROJECT_REVALIDATION_TOOL["name"]:
            return _project_revalidation(arguments)
        if name == ADVISORY_ASSESSMENT_TOOL["name"]:
            return _record_advisory_assessment(arguments)
        return base_call(name, arguments)

    setattr(call_tool, "_testamur_project_extension", True)
    _base._call_tool = call_tool


def main() -> int:
    _install()
    return int(_base.main())


if __name__ == "__main__":
    raise SystemExit(main())
