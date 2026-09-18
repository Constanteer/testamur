from __future__ import annotations

from apps.web.hosted_app import build_hosted_server
from testamur.monitor_scheduler import MonitorScheduler
from testamur.product_service import TestamurProductService
from testamur.source_fetch import SourceFetchResult


def test_scheduler_run_once_deduplicates_services_and_aggregates(monkeypatch, tmp_path):
    first = TestamurProductService(tmp_path / "first.sqlite3")
    second = TestamurProductService(tmp_path / "second.sqlite3")
    calls = []

    def fake_run_due(service):
        calls.append(service.database_path.name)
        return {
            "ok": True,
            "summary": {
                "due": 1,
                "succeeded": 1,
                "failed": 0,
                "alerts": 1 if service is first else 0,
            },
        }

    monkeypatch.setattr("testamur.monitor_scheduler.run_due_monitors", fake_run_due)
    scheduler = MonitorScheduler(lambda: [first, first, second], poll_seconds=60)
    result = scheduler.run_once()

    assert calls == ["first.sqlite3", "second.sqlite3"]
    assert result["workspace_count"] == 2
    assert result["summary"] == {
        "due": 2,
        "succeeded": 2,
        "failed": 0,
        "alerts": 1,
        "runner_errors": 0,
    }
    assert scheduler.last_result == result
    assert result["semantics"]["only_loaded_workspaces_are_scanned"] is True


def test_scheduler_isolates_workspace_runner_failure(monkeypatch, tmp_path):
    first = TestamurProductService(tmp_path / "first.sqlite3")
    second = TestamurProductService(tmp_path / "second.sqlite3")

    def fake_run_due(service):
        if service is first:
            raise RuntimeError("fixture failure")
        return {
            "ok": True,
            "summary": {"due": 0, "succeeded": 0, "failed": 0, "alerts": 0},
        }

    monkeypatch.setattr("testamur.monitor_scheduler.run_due_monitors", fake_run_due)
    scheduler = MonitorScheduler(lambda: [first, second], poll_seconds=60)
    result = scheduler.run_once()

    assert result["ok"] is False
    assert result["summary"]["runner_errors"] == 1
    assert result["workspace_count"] == 2
    assert result["workspaces"][0]["error"]["type"] == "RuntimeError"
    assert result["workspaces"][1]["ok"] is True


def test_hosted_scheduler_refreshes_due_loaded_workspace(monkeypatch, tmp_path):
    counter = {"value": 0}

    def fake_fetch(locator, *, policy=None):
        counter["value"] += 1
        return SourceFetchResult(
            locator,
            locator,
            "captured",
            f"v{counter['value']}".encode(),
            {"status_code": 200},
        )

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)

    server = build_hosted_server(
        data_dir=tmp_path,
        port=0,
        monitor_scheduler_enabled=False,
    )
    try:
        service = server.product_service_for_user("usr_scheduler")
        project = service.projects.create_project(name="Scheduled", visibility="private")
        source = service.sources.get_or_create_source("https://example.test/scheduled")
        created = service.watches.create_watch(
            service.sources,
            source_id=source["source_id"],
            interval_seconds=300,
        )
        service.projects.link_monitor(
            project_id=project["project_id"],
            watch_id=created["watch"]["watch_id"],
            source_id=source["source_id"],
        )

        assert service.watches.latest_evaluation(created["watch"]["watch_id"]) is None
        result = server.monitor_scheduler.run_once()
        assert result["summary"]["due"] == 1
        evaluation = service.watches.latest_evaluation(created["watch"]["watch_id"])
        assert evaluation["operational_state"] == "initial"
    finally:
        server.server_close()


def test_hosted_scheduler_lifecycle_can_be_enabled(tmp_path):
    server = build_hosted_server(
        data_dir=tmp_path,
        port=0,
        monitor_scheduler_enabled=True,
        monitor_scheduler_poll_seconds=60,
    )
    try:
        assert server.monitor_scheduler.running is True
    finally:
        server.server_close()
    assert server.monitor_scheduler.running is False
