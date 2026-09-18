from __future__ import annotations

import urllib.request

import pytest

from testamur.source_fetch import (
    SourceFetchPolicy,
    SourceFetchPolicyError,
    _CheckedRedirectHandler,
    _validate_locator,
    fetch_source,
)


def _addr(ip: str):
    return [(2, 1, 6, "", (ip, 443))]


def test_private_and_loopback_destinations_are_blocked_by_default(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *args, **kwargs: _addr("127.0.0.1"))
    with pytest.raises(SourceFetchPolicyError, match="non-public"):
        _validate_locator("https://example.test/private", allow_private_network=False)

    monkeypatch.setattr("socket.getaddrinfo", lambda *args, **kwargs: _addr("10.1.2.3"))
    with pytest.raises(SourceFetchPolicyError, match="non-public"):
        _validate_locator("https://example.test/private", allow_private_network=False)


def test_fetch_policy_rejects_non_schema_numeric_values():
    with pytest.raises(ValueError, match="max_bytes"):
        SourceFetchPolicy(max_bytes=10.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite positive"):
        SourceFetchPolicy(timeout_seconds=float("nan"))
    with pytest.raises(ValueError, match="max_redirects"):
        SourceFetchPolicy(max_redirects=True)  # type: ignore[arg-type]


def test_private_network_override_requires_real_boolean():
    with pytest.raises(ValueError, match="allow_private_network must be a boolean"):
        SourceFetchPolicy(allow_private_network="false")  # type: ignore[arg-type]


def test_private_network_override_is_explicit_and_skips_dns_policy_check(monkeypatch):
    def should_not_resolve(*args, **kwargs):
        raise AssertionError("DNS should not be consulted when local override is explicit")

    monkeypatch.setattr("socket.getaddrinfo", should_not_resolve)
    locator = "http://127.0.0.1:8080/spec"
    assert _validate_locator(locator, allow_private_network=True) == locator


def test_embedded_credentials_and_non_http_schemes_are_rejected_before_transport():
    with pytest.raises(SourceFetchPolicyError, match="embedded credentials"):
        _validate_locator("https://user:secret@example.com/spec", allow_private_network=False)
    with pytest.raises(SourceFetchPolicyError, match="only http"):
        _validate_locator("file:///etc/passwd", allow_private_network=False)


def test_redirect_handler_revalidates_target_and_blocks_private_redirect(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda host, *args, **kwargs: _addr("127.0.0.1"))
    history = []
    handler = _CheckedRedirectHandler(SourceFetchPolicy(), history)
    request = urllib.request.Request("https://public.example/a")
    with pytest.raises(SourceFetchPolicyError, match="non-public"):
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "http://internal.example/admin",
        )
    assert history == []


def test_redirect_limit_fails_closed_before_following_next_hop():
    policy = SourceFetchPolicy(max_redirects=0, allow_private_network=True)
    handler = _CheckedRedirectHandler(policy, [])
    request = urllib.request.Request("https://example.test/a")
    with pytest.raises(SourceFetchPolicyError, match="max_redirects=0"):
        handler.redirect_request(request, None, 302, "Found", {}, "/b")


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _Response:
    def __init__(self, body: bytes, *, final="https://example.test/spec", status=200, headers=None):
        self.body = body
        self.final = final
        self.status = status
        self.headers = _Headers(headers or {})

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.final

    def getcode(self):
        return self.status

    def read(self, amount=-1):
        return self.body if amount < 0 else self.body[:amount]


class _Opener:
    def __init__(self, response):
        self.response = response
        self.timeout = None
        self.request = None

    def open(self, request, timeout=None):
        self.request = request
        self.timeout = timeout
        return self.response


def test_fetch_ignores_ambient_proxy_and_requests_identity_encoding(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9999")
    monkeypatch.setattr("socket.getaddrinfo", lambda *args, **kwargs: _addr("8.8.8.8"))
    opener = _Opener(_Response(b"exact"))
    handlers = []

    def fake_build_opener(*items):
        handlers.extend(items)
        return opener

    monkeypatch.setattr("urllib.request.build_opener", fake_build_opener)
    result = fetch_source("https://example.test/spec")

    assert result.status == "captured"
    assert result.content == b"exact"
    assert result.metadata["policy"]["ambient_proxy_used"] is False
    proxy_handlers = [item for item in handlers if isinstance(item, urllib.request.ProxyHandler)]
    assert len(proxy_handlers) == 1
    assert proxy_handlers[0].proxies == {}
    assert opener.request.get_header("Accept-encoding") == "identity"


def test_content_length_over_limit_is_metadata_only_unavailable(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *args, **kwargs: _addr("8.8.8.8"))
    opener = _Opener(_Response(b"unused", headers={"Content-Length": "100"}))
    monkeypatch.setattr("urllib.request.build_opener", lambda *items: opener)

    result = fetch_source(
        "https://example.test/spec",
        policy=SourceFetchPolicy(max_bytes=10),
    )
    assert result.status == "unavailable"
    assert result.content is None
    assert result.metadata["error"]["kind"] == "response_too_large"


def test_stream_over_limit_is_metadata_only_unavailable(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *args, **kwargs: _addr("8.8.8.8"))
    opener = _Opener(_Response(b"01234567890"))
    monkeypatch.setattr("urllib.request.build_opener", lambda *items: opener)

    result = fetch_source(
        "https://example.test/spec",
        policy=SourceFetchPolicy(max_bytes=10),
    )
    assert result.status == "unavailable"
    assert result.content is None
    assert result.metadata["error"]["kind"] == "response_too_large"
