from __future__ import annotations

import io
import json
from datetime import datetime, timedelta

from testamur.product_actions import create_monitor, create_project, refresh_monitor, refresh_project_monitors, run_due_monitors
from testamur.product_cli import EXIT_OK, dispatch
from testamur.product_service import TestamurProductService
from testamur.source_fetch import SourceFetchResult
from testamur.web_app import dispatch_api_write


def test_refresh_monitor_revalidates_and_emits_change_alert(monkeypatch, tmp_path):
    payloads = iter([b"v1", b"v2"])

    def fake_fetch(locator, *, policy=None):
        body = next(payloads)
        return SourceFetchResult(
            requested_locator=locator,
            final_locator=locator,
            status="captured",
            content=body,
            metadata={"status_code": 200, "content_type": "text/plain"},
        )

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)

    service = TestamurProductService(tmp_path / "testamur.sqlite3")
    project = create_project(service, name="Refresh project")["project"]
    created = create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/spec",
        label="Spec",
        alert_on=["changed", "unavailable", "recovered"],
    )
    watch_id = created["watch"]["watch_id"]

    assert created["initial_evaluation"]["evaluation"]["operational_state"] == "initial"
    assert created["initial_capture"] is not None
    assert created["baseline_error"] is None

    second = refresh_monitor(service, watch_id=watch_id)
    assert second["ok"] is True
    assert second["evaluation"]["operational_state"] == "changed"
    assert second["alert"]["event_type"] == "changed"
    assert second["project"]["project_id"] == project["project_id"]

    detail = service.project(project["project_id"])
    assert detail["monitors"][0]["latest_state"] == "changed"
    assert detail["monitors"][0]["last_evaluated_at"]


def test_refresh_monitor_records_unavailable_without_fabricating_revision(monkeypatch, tmp_path):
    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(
            requested_locator=locator,
            final_locator=locator,
            status="unavailable",
            content=None,
            metadata={"error": {"kind": "transport_error", "message": "offline"}},
        )

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)

    service = TestamurProductService(tmp_path / "testamur.sqlite3")
    project = create_project(service, name="Offline project")["project"]
    created = create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/offline",
        alert_on=["unavailable"],
    )

    assert created["initial_evaluation"]["evaluation"]["operational_state"] == "unavailable"
    assert created["initial_evaluation"]["alert"]["event_type"] == "unavailable"
    assert created["initial_capture"]["revision"] is None

    refreshed = refresh_monitor(service, watch_id=created["watch"]["watch_id"])
    assert refreshed["ok"] is True
    assert refreshed["evaluation"]["operational_state"] == "unavailable"
    assert refreshed["alert"] is None
    assert refreshed["capture"]["revision"] is None
    assert refreshed["semantics"]["truth_change_implied"] is False


def test_refresh_monitor_api_contract(monkeypatch, tmp_path):
    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(locator, locator, "captured", b"api", {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)

    service = TestamurProductService(tmp_path / "testamur.sqlite3")
    project = create_project(service, name="API refresh")["project"]
    created = create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/api",
    )
    watch_id = created["watch"]["watch_id"]

    response = dispatch_api_write(
        service,
        "/v1/monitors/refresh",
        {"watch_id": watch_id},
    )
    assert response["status"] == 200
    assert response["body"]["ok"] is True
    assert response["body"]["watch_id"] == watch_id
    assert created["initial_evaluation"]["evaluation"]["operational_state"] == "initial"
    assert response["body"]["evaluation"]["operational_state"] == "unchanged"

    missing = dispatch_api_write(
        service,
        "/v1/monitors/refresh",
        {"watch_id": "tst:watch:missing"},
    )
    assert missing["status"] == 404
    assert missing["body"]["error"]["code"] == "object_not_found"


def test_monitor_refresh_cli_uses_canonical_refresh_action(monkeypatch, tmp_path):
    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(locator, locator, "captured", b"cli", {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)

    service = TestamurProductService(tmp_path / "testamur.sqlite3")
    project = create_project(service, name="CLI refresh")["project"]
    created = create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/cli",
    )
    watch_id = created["watch"]["watch_id"]

    output = io.StringIO()
    code = dispatch(
        ["monitor", "refresh", watch_id],
        stdout=output,
        service=service,
    )
    assert code == EXIT_OK
    payload = json.loads(output.getvalue())
    assert payload["schema"] == "testamur.product.monitor-refresh.v1"
    assert payload["watch_id"] == watch_id
    assert created["initial_evaluation"]["evaluation"]["operational_state"] == "initial"
    assert payload["evaluation"]["operational_state"] == "unchanged"


def test_project_refresh_runs_all_monitors_and_summarizes(monkeypatch, tmp_path):
    def fake_fetch(locator, *, policy=None):
        body = f"content:{locator}".encode("utf-8")
        return SourceFetchResult(locator, locator, "captured", body, {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)

    service = TestamurProductService(tmp_path / "testamur.sqlite3")
    project = create_project(service, name="Bulk refresh")["project"]
    first = create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/a",
    )
    second = create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/b",
    )

    refreshed = refresh_project_monitors(service, project_ref=project["slug"])
    assert refreshed["ok"] is True
    assert refreshed["summary"] == {
        "total": 2,
        "succeeded": 2,
        "failed": 0,
        "alerts": 0,
    }
    assert {item["watch_id"] for item in refreshed["results"]} == {
        first["watch"]["watch_id"],
        second["watch"]["watch_id"],
    }
    assert all(item["evaluation"]["operational_state"] == "unchanged" for item in refreshed["results"])


def test_project_refresh_is_best_effort_per_monitor(monkeypatch, tmp_path):
    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(locator, locator, "captured", locator.encode(), {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)

    service = TestamurProductService(tmp_path / "testamur.sqlite3")
    project = create_project(service, name="Best effort")["project"]
    first = create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/a",
    )
    second = create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/b",
    )
    failed_watch = first["watch"]["watch_id"]

    def fake_refresh(_service, *, watch_id):
        if watch_id == failed_watch:
            return {
                "ok": False,
                "schema": "testamur.error.v1",
                "error": {"code": "fixture_failure", "message": "fixture"},
            }
        return {
            "ok": True,
            "schema": "testamur.product.monitor-refresh.v1",
            "watch_id": watch_id,
            "evaluation": {"operational_state": "initial"},
            "alert": None,
        }

    monkeypatch.setattr("testamur.product_actions.refresh_monitor", fake_refresh)
    refreshed = refresh_project_monitors(service, project_ref=project["project_id"])
    assert refreshed["summary"] == {
        "total": 2,
        "succeeded": 1,
        "failed": 1,
        "alerts": 0,
    }
    assert refreshed["semantics"]["one_monitor_failure_does_not_abort_project_refresh"] is True
    by_watch = {item["watch_id"]: item for item in refreshed["results"]}
    assert by_watch[failed_watch]["error"]["code"] == "fixture_failure"
    assert by_watch[second["watch"]["watch_id"]]["ok"] is True


def test_project_refresh_api_and_cli(monkeypatch, tmp_path):
    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(locator, locator, "captured", locator.encode(), {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)

    service = TestamurProductService(tmp_path / "testamur.sqlite3")
    project = create_project(service, name="Bulk interfaces")["project"]
    create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/interface",
    )

    response = dispatch_api_write(
        service,
        "/v1/projects/refresh",
        {"project_ref": project["slug"]},
    )
    assert response["status"] == 200
    assert response["body"]["summary"]["succeeded"] == 1

    output = io.StringIO()
    code = dispatch(
        ["project", "refresh", project["slug"]],
        stdout=output,
        service=service,
    )
    assert code == EXIT_OK
    payload = json.loads(output.getvalue())
    assert payload["schema"] == "testamur.product.project-refresh.v1"
    assert payload["summary"]["total"] == 1


def test_run_due_monitors_skips_manual_and_respects_interval(monkeypatch, tmp_path):
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

    service = TestamurProductService(tmp_path / "testamur.sqlite3")
    project = create_project(service, name="Cadence project")["project"]
    manual = create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/manual",
        interval_seconds=None,
    )
    scheduled = create_monitor(
        service,
        project_id=project["project_id"],
        locator="https://example.test/scheduled",
        interval_seconds=300,
    )

    manual_initial = service.watches.latest_evaluation(manual["watch"]["watch_id"])
    scheduled_initial = service.watches.latest_evaluation(scheduled["watch"]["watch_id"])
    assert manual_initial is not None
    assert scheduled_initial is not None

    recorded = datetime.fromisoformat(scheduled_initial["recorded_at"].replace("Z", "+00:00"))
    not_due = run_due_monitors(service, now=recorded + timedelta(seconds=299))
    assert not_due["summary"]["due"] == 0
    assert not_due["summary"]["skipped_not_due"] == 1
    assert not_due["summary"]["skipped_manual"] == 1
    assert service.watches.latest_evaluation(manual["watch"]["watch_id"])["evaluation_id"] == manual_initial["evaluation_id"]

    due_again = run_due_monitors(service, now=recorded + timedelta(seconds=300))
    assert due_again["summary"]["due"] == 1
    assert due_again["summary"]["succeeded"] == 1
    assert due_again["results"][0]["watch_id"] == scheduled["watch"]["watch_id"]
    assert service.watches.latest_evaluation(manual["watch"]["watch_id"])["evaluation_id"] == manual_initial["evaluation_id"]


def test_monitor_cadence_flows_through_api_and_cli(monkeypatch, tmp_path):
    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(locator, locator, "captured", locator.encode(), {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)

    service = TestamurProductService(tmp_path / "testamur.sqlite3")
    project = create_project(service, name="Cadence interfaces")["project"]

    api_created = dispatch_api_write(
        service,
        "/v1/monitors",
        {
            "project_id": project["project_id"],
            "locator": "https://example.test/api-cadence",
            "interval_seconds": 900,
        },
    )
    assert api_created["status"] == 200
    assert api_created["body"]["interval_seconds"] == 900

    output = io.StringIO()
    code = dispatch(
        [
            "monitor", "add",
            "--project", project["project_id"],
            "--locator", "https://example.test/cli-cadence",
            "--interval", "1h",
        ],
        stdout=output,
        service=service,
    )
    assert code == EXIT_OK
    cli_created = json.loads(output.getvalue())
    assert cli_created["interval_seconds"] == 3600

    detail = service.project(project["project_id"])
    by_locator = {item["locator"]: item for item in detail["monitors"]}
    assert by_locator["https://example.test/api-cadence"]["interval_seconds"] == 900
    assert by_locator["https://example.test/cli-cadence"]["interval_seconds"] == 3600
