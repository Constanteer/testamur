from __future__ import annotations

import json

from testamur.blob_store import TestamurBlobStore
from testamur.environment import initialize
from testamur.front_router import main
from testamur.source_store import TestamurSourceStore


def _call(capsys, argv: list[str]):
    code = main(["--json", *argv])
    captured = capsys.readouterr()
    return code, json.loads(captured.out), captured


def test_source_retention_cli_requires_explicit_policy_and_preserves_evidence(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "workspace"
    root.mkdir()
    env = initialize(root, name="retention-cli")
    path = root / "private.bin"
    path.write_bytes(b"cli-retention-bytes")
    monkeypatch.chdir(root)

    code, uploaded, captured = _call(capsys, ["source", "upload", str(path)])
    assert code == 0, captured.err
    source_id = uploaded["source"]["source_id"]
    snapshot_id = uploaded["snapshot"]["snapshot_id"]
    revision_id = uploaded["snapshot"]["revision_id"]
    digest = uploaded["snapshot"]["content_hash"]

    code, status, captured = _call(capsys, ["source", "retention-status", source_id])
    assert code == 0, captured.err
    assert status["schema"] == "testamur.source-retention.v1"
    assert status["policy"]["raw_bytes_policy"] == "retain"
    assert status["digests"][0]["blob_present"] is True
    assert status["digests"][0]["source_reference_active"] is True

    code, refused, _ = _call(capsys, ["source", "purge", source_id])
    assert code != 0
    assert refused["error"]["code"] == "purge_not_permitted"

    code, revised, captured = _call(
        capsys, ["source", "retention", source_id, "purge_on_request"]
    )
    assert code == 0, captured.err
    assert revised["policy"]["raw_bytes_policy"] == "purge_on_request"
    assert revised["semantics"]["raw_bytes_deleted"] is False

    code, purged, captured = _call(capsys, ["source", "purge", source_id])
    assert code == 0, captured.err
    assert purged["schema"] == "testamur.source-purge.v1"
    assert purged["digests"][0]["outcome"] == "deleted"

    blobs = TestamurBlobStore(env.root / ".testamur" / "blobs")
    assert blobs.has(digest) is False

    store = TestamurSourceStore(env.database_path)
    assert store.get_source(source_id)["source_id"] == source_id
    assert store.get_snapshot(snapshot_id)["snapshot_id"] == snapshot_id
    assert store.get_revision(revision_id)["revision_id"] == revision_id

    code, status, captured = _call(capsys, ["source", "retention-status", source_id])
    assert code == 0, captured.err
    assert status["digests"][0]["blob_present"] is False
    assert status["digests"][0]["source_reference_active"] is False


def test_source_retention_cli_policy_epoch_does_not_revive_old_release(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "workspace"
    root.mkdir()
    initialize(root, name="retention-cli-epoch")
    monkeypatch.chdir(root)
    first_path = root / "a.bin"
    second_path = root / "b.bin"
    first_path.write_bytes(b"shared-cli-retention")
    second_path.write_bytes(b"shared-cli-retention")

    _, first, _ = _call(capsys, ["source", "upload", str(first_path)])
    _, second, _ = _call(capsys, ["source", "upload", str(second_path)])
    first_id = first["source"]["source_id"]
    second_id = second["source"]["source_id"]

    assert _call(capsys, ["source", "retention", first_id, "purge_on_request"])[0] == 0
    code, released, _ = _call(capsys, ["source", "purge", first_id])
    assert code == 0
    assert released["digests"][0]["outcome"] == "retained_shared_or_inflight"

    assert _call(capsys, ["source", "retention", first_id, "retain"])[0] == 0
    assert _call(capsys, ["source", "retention", first_id, "purge_on_request"])[0] == 0
    assert _call(capsys, ["source", "retention", second_id, "purge_on_request"])[0] == 0

    code, blocked, _ = _call(capsys, ["source", "purge", second_id])
    assert code == 0
    assert blocked["digests"][0]["outcome"] == "retained_shared_or_inflight"
    assert blocked["digests"][0]["active_reference_count"] == 1

    code, final, _ = _call(capsys, ["source", "purge", first_id])
    assert code == 0
    assert final["digests"][0]["outcome"] == "deleted"
