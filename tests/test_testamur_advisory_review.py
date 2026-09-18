from __future__ import annotations

from testamur.advisory_review import project_advisory_review


def candidate() -> dict:
    return {
        "event_id": "tst:advisory:event:demo",
        "event_revision_id": "tst:advisory:revision:demo-r1",
        "provider": "osv",
        "external_id": "OSV-DEMO-1",
        "status": "exact_identity_overlap",
        "matching_component_revision_ids": ["component:b", "component:a"],
    }


def assessment(subject: str, state: str, suffix: str = "1") -> dict:
    return {
        "assessment_id": f"tst:affectedness:{subject}:{suffix}",
        "event_revision_id": "tst:advisory:revision:demo-r1",
        "subject_revision": subject,
        "state": state,
        "basis": [{"kind": "advisory_revision", "ref": "tst:advisory:revision:demo-r1"}],
    }


def test_review_keeps_unassessed_exact_match_explicit() -> None:
    review = project_advisory_review(
        candidate(),
        [assessment("component:a", "NOT_APPLICABLE")],
    )

    assert review["candidate_status"] == "exact_identity_overlap"
    assert review["terminally_assessed_subject_revision_ids"] == ["component:a"]
    assert review["unassessed_subject_revision_ids"] == ["component:b"]
    assert review["requires_review"] is True
    assert review["semantics"]["candidate_is_affectedness_verdict"] is False
    assert review["semantics"]["generic_trust_score_used"] is False


def test_review_preserves_competing_current_heads() -> None:
    review = project_advisory_review(
        {**candidate(), "matching_component_revision_ids": ["component:a"]},
        [
            assessment("component:a", "CONFIRMED_AFFECTED", "scanner"),
            assessment("component:a", "NOT_APPLICABLE", "manual"),
        ],
    )

    subject = review["subjects"][0]
    assert subject["assessment_count"] == 2
    assert subject["has_competing_heads"] is True
    assert subject["states"] == ["CONFIRMED_AFFECTED", "NOT_APPLICABLE"]
    assert review["competing_subject_revision_ids"] == ["component:a"]
    assert review["requires_review"] is True
    assert review["semantics"]["multiple_heads_are_not_collapsed"] is True


def test_review_ignores_assessments_for_other_events_or_subjects() -> None:
    other_event = assessment("component:a", "MITIGATED")
    other_event["event_revision_id"] = "tst:advisory:revision:other"
    review = project_advisory_review(
        {**candidate(), "matching_component_revision_ids": ["component:a"]},
        [other_event, assessment("component:other", "DISPROVEN")],
    )

    assert review["subjects"][0]["assessment_heads"] == []
    assert review["unassessed_subject_revision_ids"] == ["component:a"]


def test_review_requires_immutable_advisory_revision_identity() -> None:
    try:
        project_advisory_review({"matching_component_revision_ids": []}, [])
    except ValueError as exc:
        assert "event_revision_id" in str(exc)
    else:
        raise AssertionError("missing immutable advisory revision must fail closed")
