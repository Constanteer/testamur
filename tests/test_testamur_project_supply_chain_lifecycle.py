from __future__ import annotations

import io
import json

from testamur.product_cli import dispatch
from testamur.product_service import TestamurProductService
from testamur.supply_chain import (
    diff_project_supply_chain,
    project_supply_chain_history,
    scan_bound_project_supply_chain,
)


def test_project_repository_binding_is_versioned_and_idempotent(tmp_path) -> None:
    service = TestamurProductService(tmp_path / "state" / "evidence.db")
    project = service.projects.create_project(name="demo")
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()

    first = service.projects.bind_repository(project["project_id"], locator=str(first_root))
    assert first["created"] is True
    assert first["changed"] is True
    assert first["revision"]["ordinal"] == 1
    assert first["revision"]["kind"] == "local-path"

    same = service.projects.bind_repository(project["project_id"], locator=str(first_root))
    assert same["created"] is False
    assert same["changed"] is False
    assert same["revision"]["binding_revision_id"] == first["revision"]["binding_revision_id"]

    second = service.projects.bind_repository(project["project_id"], locator=str(second_root))
    assert second["created"] is False
    assert second["changed"] is True
    assert second["revision"]["ordinal"] == 2
    assert second["revision"]["parent_revision_id"] == first["revision"]["binding_revision_id"]

    current = service.projects.repository_binding(project["project_id"])
    assert current is not None
    assert current["revision"]["binding_revision_id"] == second["revision"]["binding_revision_id"]
    history = service.projects.repository_binding_history(project["project_id"])
    assert [item["ordinal"] for item in history] == [2, 1]


def test_bound_existing_project_rescans_and_mechanically_diffs(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    requirements = root / "requirements.txt"
    requirements.write_text("requests==2.32.4\n", encoding="utf-8")

    service = TestamurProductService(tmp_path / "state" / "evidence.db")
    project = service.projects.create_project(name="existing")
    service.projects.bind_repository(project["project_id"], locator=str(root))

    first = scan_bound_project_supply_chain(service, project["project_id"])
    assert first["project_created"] is False
    assert first["dependency_count"] == 1

    requirements.write_text(
        "requests==2.32.5\nflask==3.1.2\n",
        encoding="utf-8",
    )
    second = scan_bound_project_supply_chain(service, project["project_id"])
    assert second["scan_revision_id"] != first["scan_revision_id"]

    diff = diff_project_supply_chain(service, project["project_id"])
    assert diff["from_scan_revision_id"] == first["scan_revision_id"]
    assert diff["to_scan_revision_id"] == second["scan_revision_id"]
    assert diff["counts"]["manifests_changed"] == 1
    assert diff["counts"]["dependencies_added"] == 1
    assert diff["counts"]["dependencies_changed"] == 1
    assert diff["counts"]["dependencies_removed"] == 0
    assert diff["dependencies"]["added"][0]["name"] == "flask"
    changed = diff["dependencies"]["changed"][0]
    assert changed["name"] == "requests"
    assert changed["version_changed"] is True
    assert [item["version"] for item in changed["before"]] == ["2.32.4"]
    assert [item["version"] for item in changed["after"]] == ["2.32.5"]
    assert diff["semantics"]["changed_implies_invalid"] is False
    assert diff["semantics"]["dependency_change_implies_vulnerable"] is False

    history = project_supply_chain_history(service, project["project_id"])
    assert [item["revision_id"] for item in history[:2]] == [
        second["scan_revision_id"],
        first["scan_revision_id"],
    ]

    projected = service.project(project["project_id"])
    assert projected["supply_chain"]["scan_revision_id"] == second["scan_revision_id"]
    assert projected["supply_chain"]["dependency_count"] == 2


def test_project_scan_cli_uses_explicit_repository_binding(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "requirements.txt").write_text("requests==2.32.5\n", encoding="utf-8")
    service = TestamurProductService(tmp_path / "state" / "evidence.db")
    project = service.projects.create_project(name="cli-demo")

    out = io.StringIO()
    assert dispatch(
        ["project", "bind-repo", project["project_id"], str(root)],
        service=service,
        stdout=out,
    ) == 0
    binding = json.loads(out.getvalue())
    assert binding["ok"] is True
    assert binding["revision"]["kind"] == "local-path"

    out = io.StringIO()
    assert dispatch(
        ["project", "scan", project["project_id"]],
        service=service,
        stdout=out,
    ) == 0
    scan = json.loads(out.getvalue())
    assert scan["ok"] is True
    assert scan["dependency_count"] == 1
    assert scan["repository_binding_revision_id"] == binding["revision"]["binding_revision_id"]

    out = io.StringIO()
    assert dispatch(
        ["project", "supply-chain", project["project_id"]],
        service=service,
        stdout=out,
    ) == 0
    supply = json.loads(out.getvalue())
    assert supply["supply_chain"]["dependency_count"] == 1
