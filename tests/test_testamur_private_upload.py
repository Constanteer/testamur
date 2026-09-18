from __future__ import annotations

import sqlite3

import pytest

from testamur.source_access import TestamurSourceAccessStore
from testamur.user_file_ingest import TestamurUserFileIngest


def test_user_upload_is_private_by_default_and_does_not_persist_local_path(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    ingest = TestamurUserFileIngest(db, tmp_path / ".testamur" / "blobs")

    result = ingest.ingest_bytes(
        b"private evidence\n",
        filename="/Users/alice/Research/secret-notes.pdf",
        owner_subject="user:alice",
    )

    source = result["source"]
    snapshot = result["snapshot"]
    policy = result["policy"]
    private_metadata = result["private_metadata"]

    assert source["initial_locator"].startswith("upload:")
    assert "/Users/alice" not in source["initial_locator"]
    assert "client_filename" not in snapshot["retrieval_metadata"]
    assert snapshot["retrieval_metadata"]["client_filename_persisted_in_snapshot"] is False
    assert snapshot["retrieval_metadata"]["media_type_persisted_in_snapshot"] is False
    assert snapshot["retrieval_metadata"]["original_local_path_persisted"] is False
    assert "secret-notes.pdf" not in str(snapshot)
    assert "/Users/alice" not in str(snapshot)
    assert private_metadata["display_name"] == "secret-notes.pdf"
    assert private_metadata["erasable"] is True
    assert policy["visibility"] == "private"
    assert policy["allow_external_processing"] is False

    access = TestamurSourceAccessStore(db)
    assert access.can_read(source["source_id"], viewer_subject=None) is False
    assert access.can_read(source["source_id"], viewer_subject="user:bob") is False
    assert access.can_read(source["source_id"], viewer_subject="user:alice") is True
    assert access.can_process_externally(
        source["source_id"], viewer_subject="user:alice"
    ) is False


def test_private_filename_can_be_erased_without_changing_evidence_identity(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    ingest = TestamurUserFileIngest(db, tmp_path / ".testamur" / "blobs")
    result = ingest.ingest_bytes(
        b"evidence",
        filename="personally-identifying-name.txt",
        owner_subject="user:alice",
    )
    source_id = result["source"]["source_id"]
    snapshot_id = result["snapshot"]["snapshot_id"]
    revision_id = result["snapshot"]["revision_id"]

    assert ingest.private_metadata.delete(source_id) is True
    assert ingest.private_metadata.get(source_id) is None
    assert ingest.sources.get_source(source_id)["source_id"] == source_id
    assert ingest.sources.get_snapshot(snapshot_id)["snapshot_id"] == snapshot_id
    assert ingest.sources.get_revision(revision_id)["revision_id"] == revision_id


def test_initial_public_upload_is_rejected_before_persistence(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    ingest = TestamurUserFileIngest(db, tmp_path / ".testamur" / "blobs")

    with pytest.raises(ValueError, match="initial user-file upload visibility must be private"):
        ingest.ingest_bytes(
            b"must begin private",
            filename="paper.txt",
            owner_subject="user:alice",
            visibility="public",
        )

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM testamur_sources").fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM testamur_source_access_policy_revisions"
        ).fetchone()[0] == 0


def test_policy_revision_can_publish_without_changing_source_or_revision_identity(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    ingest = TestamurUserFileIngest(db, tmp_path / ".testamur" / "blobs")
    result = ingest.ingest_bytes(
        b"same exact bytes",
        filename="paper.txt",
        owner_subject="user:alice",
    )
    source_id = result["source"]["source_id"]
    revision_id = result["snapshot"]["revision_id"]

    access = TestamurSourceAccessStore(db)
    second = access.record_policy(
        source_id,
        owner_subject="user:alice",
        visibility="public",
        allow_external_processing=False,
    )

    assert second["visibility"] == "public"
    assert access.can_read(source_id, viewer_subject=None) is True
    assert ingest.sources.get_source(source_id)["source_id"] == source_id
    assert ingest.sources.get_revision(revision_id)["revision_id"] == revision_id


def test_external_processing_requires_explicit_policy_opt_in(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    ingest = TestamurUserFileIngest(db, tmp_path / ".testamur" / "blobs")
    result = ingest.ingest_bytes(
        b"private model input",
        filename="input.txt",
        owner_subject="user:alice",
        allow_external_processing=True,
    )
    source_id = result["source"]["source_id"]
    access = TestamurSourceAccessStore(db)

    assert access.can_process_externally(source_id, viewer_subject=None) is False
    assert access.can_process_externally(source_id, viewer_subject="user:bob") is False
    assert access.can_process_externally(source_id, viewer_subject="user:alice") is True


def test_missing_policy_fails_closed(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    access = TestamurSourceAccessStore(db)
    assert access.can_read("tst:source:unknown", viewer_subject=None) is False
    assert access.can_read("tst:source:unknown", viewer_subject="user:alice") is False
    assert access.can_process_externally(
        "tst:source:unknown", viewer_subject="user:alice"
    ) is False


def test_policy_rows_are_append_only(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    access = TestamurSourceAccessStore(db)
    row = access.record_policy(
        "tst:source:example",
        owner_subject="user:alice",
    )

    with sqlite3.connect(db) as conn:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(
                "UPDATE testamur_source_access_policy_revisions SET visibility='public' "
                "WHERE policy_revision_id=?",
                (row["policy_revision_id"],),
            )


def test_oversize_upload_is_rejected_before_persistence(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    ingest = TestamurUserFileIngest(
        db,
        tmp_path / ".testamur" / "blobs",
        max_upload_bytes=4,
    )
    with pytest.raises(ValueError):
        ingest.ingest_bytes(
            b"12345",
            filename="too-big.bin",
            owner_subject="user:alice",
        )

    with sqlite3.connect(db) as conn:
        sources = conn.execute("SELECT COUNT(*) FROM testamur_sources").fetchone()[0]
        policies = conn.execute(
            "SELECT COUNT(*) FROM testamur_source_access_policy_revisions"
        ).fetchone()[0]
    assert sources == 0
    assert policies == 0

def test_mutable_media_type_is_not_part_of_immutable_snapshot(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    ingest = TestamurUserFileIngest(db, tmp_path / ".testamur" / "blobs")
    result = ingest.ingest_bytes(
        b"private image bytes",
        filename="secret-name.png",
        media_type="image/png",
        owner_subject="user:alice",
    )
    snapshot = result["snapshot"]
    assert "image/png" not in str(snapshot)
    assert "secret-name.png" not in str(snapshot)
    assert result["private_metadata"]["media_type"] == "image/png"


def test_external_processing_flag_requires_real_boolean(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    ingest = TestamurUserFileIngest(db, tmp_path / ".testamur" / "blobs")
    with pytest.raises(ValueError, match="allow_external_processing must be a boolean"):
        ingest.ingest_bytes(
            b"private",
            filename="input.txt",
            owner_subject="user:alice",
            allow_external_processing="false",
        )
