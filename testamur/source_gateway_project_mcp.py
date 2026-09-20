from __future__ import annotations

from typing import Any, Mapping

from . import source_gateway_mcp as _base


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


def _install() -> None:
    if not any(tool.get("name") == PROJECT_REVALIDATION_TOOL["name"] for tool in _base.TOOLS):
        _base.TOOLS.append(PROJECT_REVALIDATION_TOOL)
    base_call = _base._call_tool
    if getattr(base_call, "_testamur_project_revalidation", False):
        return

    def call_tool(name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if name == PROJECT_REVALIDATION_TOOL["name"]:
            return _project_revalidation(arguments)
        return base_call(name, arguments)

    setattr(call_tool, "_testamur_project_revalidation", True)
    _base._call_tool = call_tool


def main() -> int:
    _install()
    return int(_base.main())


if __name__ == "__main__":
    raise SystemExit(main())
