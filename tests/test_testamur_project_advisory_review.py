from __future__ import annotations

from testamur.affectedness import AffectednessState, TestamurAffectednessStore
from testamur.project_advisory_review import project_advisory_reviews


def _candidate(event_revision_id: str = "eventrev:1") -> dict[str, object]:
    return {
        "event_id": "event:1",
        "event_revision_id": event_revision_id,
        "provider": "osv",
        "external_id": "CVE-TEST-1",
        "matching_component_revision_ids": ["componentrev:a"],
        "status": "exact_identity_overlap",
    }


def test_project_review_keeps_exact_match_unassessed(tmp_path):
    reviews = project_advisory_reviews(tmp_path / "testamur.db", [_candidate()])

    assert len(reviews) == 1
    review = reviews[0]
    assert review["requires_review"] is True
    assert review["unassessed_subject_revision_ids"] == ["componentrev:a"]
    assert review["terminally_assessed_subject_revision_ids"] == []
    assert review["semantics"]["candidate_is_affectedness_verdict"] is False
    assert review["semantics"]["generic_trust_score_used"] is False


def test_project_review_surfaces_terminal_recorded_assessment(tmp_path):
    database = tmp_path / "testamur.db"
    store = TestamurAffectednessStore(database)
    store.record_assessment(
        event_id="event:1",
        event_revision_id="eventrev:1",
        subject_revision="componentrev:a",
        state=AffectednessState.CONFIRMED_AFFECTED,
        basis=[{"kind": "advisory_revision", "ref": "eventrev:1"}],
        evidence=[{
            "ref": "evidence:material-present",
            "signal": "MATERIAL_PRESENT",
            "evidence_class": "OBSERVED",
        }],
    )

    review = project_advisory_reviews(database, [_candidate()])[0]

    assert review["requires_review"] is False
    assert review["terminally_assessed_subject_revision_ids"] == ["componentrev:a"]
    assert review["subjects"][0]["states"] == ["CONFIRMED_AFFECTED"]


def test_project_review_preserves_competing_unsuperseded_heads(tmp_path):
    database = tmp_path / "testamur.db"
    store = TestamurAffectednessStore(database)
    for ref, signal, state in (
        ("evidence:present", "MATERIAL_PRESENT", AffectednessState.CONFIRMED_AFFECTED),
        ("evidence:absent", "MATERIAL_ABSENT", AffectednessState.DISPROVEN),
    ):
        store.record_assessment(
            event_id="event:1",
            event_revision_id="eventrev:1",
            subject_revision="componentrev:a",
            state=state,
            basis=[{"kind": "advisory_revision", "ref": "eventrev:1"}],
            evidence=[{"ref": ref, "signal": signal, "evidence_class": "OBSERVED"}],
        )

    review = project_advisory_reviews(database, [_candidate()])[0]

    assert review["requires_review"] is True
    assert review["competing_subject_revision_ids"] == ["componentrev:a"]
    assert review["subjects"][0]["assessment_count"] == 2
    assert review["subjects"][0]["states"] == ["CONFIRMED_AFFECTED", "DISPROVEN"]


def test_project_review_rejects_candidate_without_immutable_revision(tmp_path):
    candidate = _candidate()
    candidate["event_revision_id"] = ""

    try:
        project_advisory_reviews(tmp_path / "testamur.db", [candidate])
    except ValueError as exc:
        assert "event_revision_id" in str(exc)
    else:
        raise AssertionError("missing immutable advisory revision must fail closed")
