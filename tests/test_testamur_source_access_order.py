from __future__ import annotations

from testamur.source_access import TestamurSourceAccessStore


def test_later_appended_private_policy_wins_even_with_earlier_recorded_at(tmp_path):
    db = tmp_path / ".testamur" / "evidence.sqlite3"
    access = TestamurSourceAccessStore(db)
    source_id = "tst:source:policy-order"

    access.record_policy(
        source_id,
        owner_subject="user:alice",
        visibility="public",
        recorded_at="2030-01-01T00:00:00Z",
    )
    revoked = access.record_policy(
        source_id,
        owner_subject="user:alice",
        visibility="private",
        recorded_at="2020-01-01T00:00:00Z",
    )

    assert access.latest_policy(source_id)["policy_revision_id"] == revoked["policy_revision_id"]
    assert access.can_read(source_id, viewer_subject=None) is False
    assert access.can_read(source_id, viewer_subject="user:alice") is True
