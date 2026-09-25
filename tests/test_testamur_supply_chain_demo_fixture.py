from __future__ import annotations

from pathlib import Path
import shutil

from testamur.product_service import TestamurProductService
from testamur.supply_chain import diff_project_supply_chain, scan_bound_project_supply_chain


FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "supply-chain-demo"


def test_deterministic_demo_fixture_runs_real_project_scan_and_diff(tmp_path) -> None:
    """Keep the launch/demo input executable through the real Project lifecycle."""
    baseline = FIXTURE / "baseline"
    current = FIXTURE / "current"
    assert (baseline / "requirements.txt").read_text(encoding="utf-8").splitlines()[-2:] == [
        "requests==2.32.4",
        "flask==3.0.3",
    ]
    assert (current / "requirements.txt").read_text(encoding="utf-8").splitlines()[-1:] == [
        "requests==2.32.5",
    ]

    repo = tmp_path / "demo-repo"
    shutil.copytree(baseline, repo)

    service = TestamurProductService(tmp_path / "state" / "evidence.db")
    project = service.projects.create_project(name="deterministic-demo")
    service.projects.bind_repository(project["project_id"], locator=str(repo))

    first = scan_bound_project_supply_chain(service, project["project_id"])
    assert first["dependency_count"] == 2

    shutil.rmtree(repo)
    shutil.copytree(current, repo)
    second = scan_bound_project_supply_chain(service, project["project_id"])
    assert second["scan_revision_id"] != first["scan_revision_id"]
    assert second["dependency_count"] == 1

    diff = diff_project_supply_chain(service, project["project_id"])
    assert diff["counts"]["dependencies_added"] == 0
    assert diff["counts"]["dependencies_changed"] == 1
    assert diff["counts"]["dependencies_removed"] == 1

    changed = diff["dependencies"]["changed"][0]
    assert changed["name"] == "requests"
    assert [item["version"] for item in changed["before"]] == ["2.32.4"]
    assert [item["version"] for item in changed["after"]] == ["2.32.5"]
    assert changed["version_transition"] == "upgraded"
    assert diff["semantics"]["version_transition_is_mechanical"] is True

    removed = diff["dependencies"]["removed"][0]
    assert removed["name"] == "flask"

    # Demo observations remain evidence. They do not smuggle in verdicts.
    assert diff["semantics"]["changed_implies_invalid"] is False
    assert diff["semantics"]["dependency_change_implies_vulnerable"] is False
    assert diff["semantics"]["affectedness_inferred"] is False
    assert diff["semantics"]["generic_trust_score_used"] is False
