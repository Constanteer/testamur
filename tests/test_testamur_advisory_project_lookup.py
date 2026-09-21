from testamur.advisory import AdverseEventClass, TestamurAdvisoryStore
from testamur.advisory_project_lookup import latest_advisory_revisions_for_upstream_refs


def _record(store, external_id, upstream_ref):
    return store.record_adverse_event(
        provider="fixture",
        external_id=external_id,
        event_class=AdverseEventClass.VULNERABILITY_ADVISORY,
        upstream_refs=[upstream_ref],
        source_refs=[f"source:{external_id}"],
    )


def test_exact_project_lookup_is_not_bounded_by_global_latest_window(tmp_path):
    store = TestamurAdvisoryStore(tmp_path / "testamur.sqlite3")
    target_ref = "component-revision:target"
    target = _record(store, "target", target_ref)

    # Make the target older than the Product projection's historical 1000-event
    # inventory window. None of these unrelated events may hide the exact match.
    for index in range(1001):
        _record(store, f"noise-{index}", f"component-revision:noise-{index}")

    assert target not in store.latest_revisions(limit=1000)
    matches = latest_advisory_revisions_for_upstream_refs(store, [target_ref])
    assert [item["event_revision_id"] for item in matches] == [
        target["event_revision_id"]
    ]
    assert matches[0]["semantics"]["affectedness_is_separate_object"] is True


def test_exact_project_lookup_uses_latest_revision_only(tmp_path):
    store = TestamurAdvisoryStore(tmp_path / "testamur.sqlite3")
    old_ref = "component-revision:old"
    new_ref = "component-revision:new"
    first = _record(store, "moving", old_ref)
    latest = store.record_adverse_event(
        provider="fixture",
        external_id="moving",
        event_class=AdverseEventClass.VULNERABILITY_ADVISORY,
        upstream_refs=[new_ref],
        source_refs=["source:moving:2"],
    )

    assert first["event_revision_id"] != latest["event_revision_id"]
    assert latest_advisory_revisions_for_upstream_refs(store, [old_ref]) == []
    assert [
        item["event_revision_id"]
        for item in latest_advisory_revisions_for_upstream_refs(store, [new_ref])
    ] == [latest["event_revision_id"]]
