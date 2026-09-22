from __future__ import annotations

import pytest

from testamur import repository_binding_mcp as binding_mcp
from testamur.product_service import TestamurProductService


def _state(monkeypatch, tmp_path):
    db = tmp_path / "state" / "evidence.db"
    monkeypatch.setattr(binding_mcp._base, "_db_path", lambda: db)
    return TestamurProductService.integrated(db)


def test_binding_lifecycle_tools_are_host_neutral_and_non_verdict_bearing():
    binding_mcp._install()
    tools = {tool["name"]: tool for tool in binding_mcp._base.TOOLS}
    for name in (
        "testamur.project_repository_binding",
        "testamur.set_project_repository_binding_enabled",
        "testamur.project_repository_unbind",
    ):
        assert name in tools
        properties = tools[name]["inputSchema"]["properties"]
        assert "verdict" not in properties
        assert "trust_score" not in properties


def test_mcp_unbind_blocks_project_scan_without_deleting_binding(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "requirements.txt").write_text("requests==2.32.0\n", encoding="utf-8")
    service = _state(monkeypatch, tmp_path)
    project = service.projects.create_project(name="mcp-binding")
    created = service.projects.bind_repository(project["project_id"], locator=str(root))

    binding_mcp._install()
    disabled = binding_mcp._unbind({"project_ref": project["project_id"]})
    assert disabled["binding"]["enabled"] is False
    assert disabled["semantics"]["binding_state_implies_content_observed"] is False

    with pytest.raises(ValueError, match="is disabled"):
        binding_mcp._base._call_tool(
            "testamur.project_scan", {"project_ref": project["project_id"]}
        )

    current = service.projects.repository_binding(project["project_id"])
    assert current is not None
    assert current["binding_id"] == created["binding"]["binding_id"]
    assert current["revision"]["binding_revision_id"] == created["revision"]["binding_revision_id"]

    enabled = binding_mcp._set_binding(
        {"project_ref": project["project_id"], "enabled": True}
    )
    assert enabled["binding"]["enabled"] is True
    scanned = binding_mcp._base._call_tool(
        "testamur.project_scan", {"project_ref": project["project_id"]}
    )
    assert scanned["ok"] is True
    assert scanned["semantics"]["recorded_is_not_verified"] is True
