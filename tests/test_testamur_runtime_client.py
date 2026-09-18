from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from testamur.runtime_client import HttpRuntimeClient


class _Response:
    def __init__(self, value: object) -> None:
        self._body = json.dumps(value).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_runtime_client_normalizes_endpoint_and_keeps_transport_semantics_narrow() -> None:
    client = HttpRuntimeClient("https://runtime.example.test///")
    assert client.endpoint == "https://runtime.example.test"
    assert client.execution_filesystem_scope == "remote_or_unknown"

    with patch("urllib.request.urlopen", return_value=_Response({"mode": "hosted"})) as urlopen:
        assert client.status() == {"mode": "hosted"}
        assert urlopen.call_args.args[0] == "https://runtime.example.test/v1/status"


def test_runtime_client_rejects_empty_endpoint() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        HttpRuntimeClient("  ")


def test_runtime_client_rejects_non_object_wire_response() -> None:
    client = HttpRuntimeClient("https://runtime.example.test")
    with patch("urllib.request.urlopen", return_value=_Response(["not", "an", "envelope"])):
        with pytest.raises(RuntimeError, match="non-object response"):
            client.status()
