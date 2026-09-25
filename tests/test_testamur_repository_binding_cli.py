import io

from testamur.product_service import TestamurProductService
from testamur.repository_binding_cli import dispatch


def test_repository_binding_cli_disable_blocks_scan_and_reenable_restores_it(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("requests==2.32.0\n", encoding="utf-8")
    service = TestamurProductService.integrated(tmp_path / "testamur.sqlite3")
    project = service.projects.create_project(name="Lifecycle CLI")
    service.projects.bind_repository(project["project_id"], locator=str(repo))

    out = io.StringIO()
    assert dispatch(["disable", project["project_id"]], stdout=out, service=service) == 0
    assert '"enabled":false' in out.getvalue()

    out = io.StringIO()
    assert dispatch(["scan", project["project_id"]], stdout=out, service=service) == 2
    assert "is disabled" in out.getvalue()
    assert service.records.stats()["records"] == 0

    out = io.StringIO()
    assert dispatch(["enable", project["project_id"]], stdout=out, service=service) == 0
    assert '"enabled":true' in out.getvalue()

    out = io.StringIO()
    assert dispatch(["scan", project["project_id"]], stdout=out, service=service) == 0
    assert '"testamur.supply-chain.project-scan-action.v1"' in out.getvalue()


def test_repository_binding_cli_unbind_preserves_binding_history(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    service = TestamurProductService.integrated(tmp_path / "testamur.sqlite3")
    project = service.projects.create_project(name="History")
    created = service.projects.bind_repository(project["project_id"], locator=str(repo))

    out = io.StringIO()
    assert dispatch(["unbind", project["project_id"]], stdout=out, service=service) == 0
    current = service.projects.repository_binding(project["project_id"])
    assert current is not None
    assert current["binding_id"] == created["binding"]["binding_id"]
    assert current["revision"]["binding_revision_id"] == created["revision"]["binding_revision_id"]
