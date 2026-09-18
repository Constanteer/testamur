from __future__ import annotations

import json

from testamur.environment import initialize
from testamur.front_router import main


def test_source_upload_cli_creates_private_source_without_local_path_leak(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "workspace"
    root.mkdir()
    initialize(root, name="private-upload-cli")
    sensitive_dir = root / "Users" / "alice" / "Secret Project"
    sensitive_dir.mkdir(parents=True)
    path = sensitive_dir / "private-report.pdf"
    path.write_bytes(b"%PDF-private-cli-bytes")
    monkeypatch.chdir(root)

    code = main(["--json", "source", "upload", str(path)])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["schema"] == "testamur.source-upload.v1"
    assert payload["source"]["initial_locator"].startswith("upload:")
    assert payload["policy"]["visibility"] == "private"
    assert payload["policy"]["allow_external_processing"] is False
    assert payload["private_metadata"]["display_name"] == "private-report.pdf"
    assert payload["snapshot"]["content_hash"] == payload["blob"]["content_hash"]

    rendered = captured.out
    assert str(sensitive_dir) not in rendered
    assert "Secret Project" not in rendered
    assert "private-report.pdf" not in json.dumps(payload["snapshot"], sort_keys=True)


def test_source_upload_cli_missing_file_has_stable_machine_error(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "workspace"
    root.mkdir()
    initialize(root, name="private-upload-cli-missing")
    monkeypatch.chdir(root)

    missing = root / "does-not-exist" / "secret.txt"
    code = main(["--json", "source", "upload", str(missing)])
    captured = capsys.readouterr()
    assert code != 0
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    assert payload["schema"] == "testamur.error.v1"
    assert payload["error"]["code"] == "file_not_found"
    assert str(missing) not in captured.out


def test_front_help_mentions_private_source_upload(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["--help"])
    assert code == 0
    rendered = capsys.readouterr().out
    assert "testamur source upload <file>" in rendered
    assert "begin private" in rendered
