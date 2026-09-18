from __future__ import annotations

from testamur.source_fetch import SourceFetchResult
from testamur.source_gateway_mcp import MODERN_VERSION, handle_request


def _modern(method: str, request_id=1, **params):
    value = dict(params)
    value["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": MODERN_VERSION,
        "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "1"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": value}


def _legacy_initialize(version: str):
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": version,
            "capabilities": {},
            "clientInfo": {"name": "legacy", "version": "1"},
        },
    }


def test_modern_discovery_and_tools_list():
    discovered = handle_request(_modern("server/discover", request_id="d"))
    assert discovered["result"]["resultType"] == "complete"
    assert MODERN_VERSION in discovered["result"]["supportedVersions"]
    assert discovered["result"]["capabilities"]["tools"] == {}

    listed = handle_request(_modern("tools/list"))
    assert listed["result"]["resultType"] == "complete"
    names = [tool["name"] for tool in listed["result"]["tools"]]
    assert names == [
        "testamur.fetch",
        "testamur.open_revision",
        "testamur.source_status",
        "testamur.revalidate",
        "testamur.watch_refresh",
    ]


def test_legacy_initialize_is_still_supported():
    response = handle_request(_legacy_initialize("2025-11-25"))
    assert response["result"]["protocolVersion"] == "2025-11-25"
    assert response["result"]["capabilities"]["tools"] == {}


def test_initialize_rejects_unknown_protocol_instead_of_echoing_it():
    response = handle_request(_legacy_initialize("2099-01-01"))
    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["requested"] == "2099-01-01"
    assert "2025-11-25" in response["error"]["data"]["supported"]


def test_fetch_tool_returns_content_and_exact_revision(monkeypatch, tmp_path):
    monkeypatch.setenv("TESTAMUR_DB", str(tmp_path / "evidence.db"))

    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(locator, locator, "captured", b"hello gateway", {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    response = handle_request(
        _modern(
            "tools/call",
            name="testamur.fetch",
            arguments={"locator": "https://example.test/spec"},
        )
    )
    result = response["result"]
    assert result["isError"] is False
    assert result["resultType"] == "complete"
    payload = result["structuredContent"]
    assert payload["revision"]["revision_id"].startswith("tst:revision:")
    assert payload["content"]["encoding"] == "utf-8"
    assert payload["content"]["text"] == "hello gateway"
    assert payload["semantics"]["durable_reliance_implied"] is False


def test_open_revision_over_return_limit_is_metadata_not_tool_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("TESTAMUR_DB", str(tmp_path / "evidence.db"))
    body = b"0123456789"

    def fake_fetch(locator, *, policy=None):
        return SourceFetchResult(locator, locator, "captured", body, {"status_code": 200})

    monkeypatch.setattr("testamur.source_gateway.fetch_source", fake_fetch)
    captured = handle_request(
        _modern(
            "tools/call",
            name="testamur.fetch",
            arguments={"locator": "https://example.test/large", "max_return_bytes": 100},
        )
    )
    revision_id = captured["result"]["structuredContent"]["revision"]["revision_id"]

    opened = handle_request(
        _modern(
            "tools/call",
            name="testamur.open_revision",
            arguments={"revision_id": revision_id, "max_return_bytes": 4},
        )
    )
    assert opened["result"]["isError"] is False
    payload = opened["result"]["structuredContent"]
    assert payload["content"]["content_available"] is True
    assert payload["content"]["content_returned"] is False
    assert payload["content"]["byte_size"] == len(body)
    assert payload["blob"]["integrity_verified"] is True


def test_mcp_rejects_non_schema_numeric_values(monkeypatch, tmp_path):
    monkeypatch.setenv("TESTAMUR_DB", str(tmp_path / "evidence.db"))

    as_string = handle_request(
        _modern(
            "tools/call",
            name="testamur.fetch",
            arguments={"locator": "https://example.test/spec", "max_bytes": "10"},
        )
    )
    assert as_string["error"]["code"] == -32602
    assert "max_bytes must be an integer" in as_string["error"]["message"]

    nan_timeout = handle_request(
        _modern(
            "tools/call",
            name="testamur.fetch",
            arguments={"locator": "https://example.test/spec", "timeout_seconds": float("nan")},
        )
    )
    assert nan_timeout["error"]["code"] == -32602
    assert "finite positive number" in nan_timeout["error"]["message"]

    bool_redirects = handle_request(
        _modern(
            "tools/call",
            name="testamur.fetch",
            arguments={"locator": "https://example.test/spec", "max_redirects": True},
        )
    )
    assert bool_redirects["error"]["code"] == -32602
    assert "max_redirects must be an integer" in bool_redirects["error"]["message"]


def test_private_network_override_rejects_string_false(monkeypatch, tmp_path):
    monkeypatch.setenv("TESTAMUR_DB", str(tmp_path / "evidence.db"))
    response = handle_request(
        _modern(
            "tools/call",
            name="testamur.fetch",
            arguments={
                "locator": "https://example.test/spec",
                "allow_private_network": "false",
            },
        )
    )
    assert response["error"]["code"] == -32602
    assert "allow_private_network must be a boolean" in response["error"]["message"]


def test_unknown_tool_is_invalid_params():
    response = handle_request(_modern("tools/call", name="testamur.nope", arguments={}))
    assert response["error"]["code"] == -32602
    assert "unknown tool" in response["error"]["message"]


def test_notification_has_no_response():
    assert handle_request({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) is None
