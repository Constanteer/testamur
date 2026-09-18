from __future__ import annotations

import sqlite3

import pytest

from testamur.blob_store import BlobIntegrityError
from testamur.user_file_ingest import TestamurUserFileIngest


def _ingest(tmp_path, content: bytes, *, raw_bytes_policy: str = "purge_on_request"):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    blobs = tmp_path / ".testamur" / "blobs"
    ingest = TestamurUserFileIngest(db, blobs)
    result = ingest.ingest_bytes(
        content,
        filename="private.bin",
        owner_subject="user:alice",
        raw_bytes_policy=raw_bytes_policy,
    )
    return ingest, result


def test_single_source_purge_deletes_bytes_but_preserves_evidence_identity(tmp_path):
    ingest, result = _ingest(tmp_path, b"private-retention-single")
    source_id = result["source"]["source_id"]
    snapshot_id = result["snapshot"]["snapshot_id"]
    revision_id = result["snapshot"]["revision_id"]
    digest = result["snapshot"]["content_hash"]

    assert ingest.blobs.has(digest, verify=True)
    purged = ingest.retention.purge_source(source_id, owner_subject="user:alice")
    assert purged["digests"][0]["outcome"] == "deleted"
    assert ingest.blobs.has(digest) is False

    assert ingest.sources.get_source(source_id)["source_id"] == source_id
    assert ingest.sources.get_snapshot(snapshot_id)["snapshot_id"] == snapshot_id
    assert ingest.sources.get_revision(revision_id)["revision_id"] == revision_id
    assert ingest.private_metadata.get(source_id)["display_name"] == "private.bin"

    repeated = ingest.retention.purge_source(source_id, owner_subject="user:alice")
    assert repeated["digests"][0]["outcome"] == "already_absent"
    assert (
        repeated["digests"][0]["retention_event_id"]
        == purged["digests"][0]["retention_event_id"]
    )


def test_purge_refuses_retain_policy_until_owner_changes_policy(tmp_path):
    ingest, result = _ingest(
        tmp_path,
        b"retain-policy",
        raw_bytes_policy="retain",
    )
    source_id = result["source"]["source_id"]
    digest = result["snapshot"]["content_hash"]

    with pytest.raises(PermissionError, match="does not permit purge"):
        ingest.retention.purge_source(source_id, owner_subject="user:alice")
    with pytest.raises(PermissionError, match="does not permit release"):
        ingest.retention.record_event(
            source_id,
            digest,
            owner_subject="user:alice",
            action="release",
        )
    assert ingest.blobs.has(digest, verify=True)
    assert ingest.retention.latest_event(source_id, digest) is None


def test_shared_digest_is_not_deleted_until_every_source_releases_it(tmp_path):
    ingest, first = _ingest(tmp_path, b"same-shared-bytes")
    _, second = _ingest(tmp_path, b"same-shared-bytes")
    first_source = first["source"]["source_id"]
    second_source = second["source"]["source_id"]
    digest = first["snapshot"]["content_hash"]

    assert second["snapshot"]["content_hash"] == digest
    assert first_source != second_source

    first_purge = ingest.retention.purge_source(first_source, owner_subject="user:alice")
    assert first_purge["digests"][0]["outcome"] == "retained_shared_or_inflight"
    assert first_purge["digests"][0]["active_reference_count"] == 1
    assert ingest.blobs.has(digest, verify=True)

    second_purge = ingest.retention.purge_source(second_source, owner_subject="user:alice")
    assert second_purge["digests"][0]["outcome"] == "deleted"
    assert ingest.blobs.has(digest) is False


def test_inflight_claim_blocks_final_delete_until_writer_releases_claim(tmp_path):
    ingest, result = _ingest(tmp_path, b"claimed-bytes")
    source_id = result["source"]["source_id"]
    digest = result["snapshot"]["content_hash"]
    claim = ingest.retention.claim(
        "tst:source:pending-writer",
        digest,
        purpose="test_pending_capture",
    )

    blocked = ingest.retention.purge_source(source_id, owner_subject="user:alice")
    assert blocked["digests"][0]["outcome"] == "retained_shared_or_inflight"
    assert blocked["digests"][0]["active_reference_count"] == 0
    assert blocked["digests"][0]["active_ingest_claim_count"] == 1
    assert ingest.blobs.has(digest, verify=True)

    assert ingest.retention.release_claim(claim["claim_id"]) is True
    deleted = ingest.retention.purge_source(source_id, owner_subject="user:alice")
    assert deleted["digests"][0]["outcome"] == "deleted"
    assert ingest.blobs.has(digest) is False


def test_current_retain_policy_blocks_delete_before_retain_event_is_appended(tmp_path):
    ingest, first = _ingest(tmp_path, b"policy-window-shared")
    _, second = _ingest(tmp_path, b"policy-window-shared")
    first_source = first["source"]["source_id"]
    second_source = second["source"]["source_id"]
    digest = first["snapshot"]["content_hash"]

    first_purge = ingest.retention.purge_source(first_source, owner_subject="user:alice")
    assert first_purge["digests"][0]["outcome"] == "retained_shared_or_inflight"
    assert ingest.retention.latest_event(first_source, digest)["action"] == "release"

    latest = ingest.access.latest_policy(first_source)
    ingest.access.record_policy(
        first_source,
        owner_subject="user:alice",
        visibility=latest["visibility"],
        raw_bytes_policy="retain",
        allow_external_processing=latest["allow_external_processing"],
    )
    # Simulate the exact inter-transaction window: policy is already retain but
    # the explicit retain event has not been appended yet.
    assert ingest.retention.latest_event(first_source, digest)["action"] == "release"

    second_purge = ingest.retention.purge_source(second_source, owner_subject="user:alice")
    assert second_purge["digests"][0]["outcome"] == "retained_shared_or_inflight"
    assert second_purge["digests"][0]["active_reference_count"] == 1
    assert ingest.blobs.has(digest, verify=True)


def test_explicit_retain_event_can_reacquire_shared_digest_after_release(tmp_path):
    ingest, first = _ingest(tmp_path, b"reacquire-shared")
    _, second = _ingest(tmp_path, b"reacquire-shared")
    first_source = first["source"]["source_id"]
    second_source = second["source"]["source_id"]
    digest = first["snapshot"]["content_hash"]

    first_purge = ingest.retention.purge_source(first_source, owner_subject="user:alice")
    assert first_purge["digests"][0]["outcome"] == "retained_shared_or_inflight"
    assert ingest.retention.latest_event(first_source, digest)["action"] == "release"

    latest = ingest.access.latest_policy(first_source)
    ingest.access.record_policy(
        first_source,
        owner_subject="user:alice",
        visibility=latest["visibility"],
        raw_bytes_policy="retain",
        allow_external_processing=latest["allow_external_processing"],
    )
    retained = ingest.retention.retain_source(first_source, owner_subject="user:alice")
    assert retained["retained_digest_count"] == 1
    assert ingest.retention.latest_event(first_source, digest)["action"] == "retain"

    second_purge = ingest.retention.purge_source(second_source, owner_subject="user:alice")
    assert second_purge["digests"][0]["outcome"] == "retained_shared_or_inflight"
    assert second_purge["digests"][0]["active_reference_count"] == 1
    assert ingest.blobs.has(digest, verify=True)

    latest = ingest.access.latest_policy(first_source)
    ingest.access.record_policy(
        first_source,
        owner_subject="user:alice",
        visibility=latest["visibility"],
        raw_bytes_policy="purge_on_request",
        allow_external_processing=latest["allow_external_processing"],
    )
    final = ingest.retention.purge_source(first_source, owner_subject="user:alice")
    assert final["digests"][0]["outcome"] == "deleted"
    assert ingest.blobs.has(digest) is False


def test_old_release_does_not_revive_after_policy_epoch_change(tmp_path):
    ingest, first = _ingest(tmp_path, b"policy-epoch-shared")
    _, second = _ingest(tmp_path, b"policy-epoch-shared")
    first_source = first["source"]["source_id"]
    second_source = second["source"]["source_id"]
    digest = first["snapshot"]["content_hash"]

    released = ingest.retention.purge_source(first_source, owner_subject="user:alice")
    assert released["digests"][0]["outcome"] == "retained_shared_or_inflight"
    old_event = ingest.retention.latest_event(first_source, digest)
    old_policy_revision = old_event["policy_revision_id"]

    latest = ingest.access.latest_policy(first_source)
    ingest.access.record_policy(
        first_source,
        owner_subject="user:alice",
        visibility=latest["visibility"],
        raw_bytes_policy="retain",
        allow_external_processing=latest["allow_external_processing"],
    )
    latest = ingest.access.latest_policy(first_source)
    new_policy = ingest.access.record_policy(
        first_source,
        owner_subject="user:alice",
        visibility=latest["visibility"],
        raw_bytes_policy="purge_on_request",
        allow_external_processing=latest["allow_external_processing"],
    )
    assert new_policy["policy_revision_id"] != old_policy_revision

    # The release belongs to the previous policy epoch, so it must fail closed
    # instead of silently becoming active again.
    second_purge = ingest.retention.purge_source(second_source, owner_subject="user:alice")
    assert second_purge["digests"][0]["outcome"] == "retained_shared_or_inflight"
    assert second_purge["digests"][0]["active_reference_count"] == 1
    assert ingest.blobs.has(digest, verify=True)

    renewed = ingest.retention.purge_source(first_source, owner_subject="user:alice")
    assert renewed["digests"][0]["outcome"] == "deleted"
    new_event = ingest.retention.latest_event(first_source, digest)
    assert new_event["policy_revision_id"] == new_policy["policy_revision_id"]
    assert new_event["event_id"] != old_event["event_id"]


def test_corrupt_blob_is_never_silently_deleted_and_release_rolls_back(tmp_path):
    ingest, result = _ingest(tmp_path, b"integrity-sensitive")
    source_id = result["source"]["source_id"]
    digest = result["snapshot"]["content_hash"]
    ingest.blobs._path(digest).write_bytes(b"tampered")

    with pytest.raises(BlobIntegrityError, match="refusing to delete corrupt blob"):
        ingest.retention.purge_source(source_id, owner_subject="user:alice")

    assert ingest.blobs.has(digest) is True
    assert ingest.blobs.has(digest, verify=True) is False
    assert ingest.retention.latest_event(source_id, digest) is None


def test_retention_events_are_append_only(tmp_path):
    ingest, result = _ingest(tmp_path, b"append-only-retention")
    source_id = result["source"]["source_id"]
    digest = result["snapshot"]["content_hash"]
    event = ingest.retention.record_event(
        source_id,
        digest,
        owner_subject="user:alice",
        action="retain",
    )

    with sqlite3.connect(ingest.database_path) as conn:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(
                "UPDATE testamur_blob_retention_events SET action='release' WHERE event_id=?",
                (event["event_id"],),
            )
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(
                "DELETE FROM testamur_blob_retention_events WHERE event_id=?",
                (event["event_id"],),
            )
