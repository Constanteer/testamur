from testamur.project_advisory_guidance import project_advisory_guidance


def test_empty_candidates_do_not_claim_unaffected():
    guidance = project_advisory_guidance([])

    assert guidance["state"] == "no-candidates"
    assert guidance["next_action"] == "inspect-inventory"
    assert guidance["semantics"]["no_candidate_proves_unaffected"] is False
    assert "not proof" in guidance["detail"]


def test_exact_overlap_routes_to_review_without_affectedness_claim():
    guidance = project_advisory_guidance([
        {
            "status": "exact_identity_overlap",
            "requires_review": True,
            "matching_component_revision_ids": ["tst:component-revision:example"],
        }
    ])

    assert guidance["state"] == "review-required"
    assert guidance["review_required_count"] == 1
    assert guidance["next_action"] == "review-candidates"
    assert guidance["semantics"]["identity_overlap_is_affectedness_verdict"] is False
    assert guidance["semantics"]["generic_trust_score_used"] is False


def test_competing_heads_take_priority_over_generic_review_prompt():
    guidance = project_advisory_guidance([
        {
            "requires_review": True,
            "competing_subject_revision_ids": ["asr_1", "asr_2"],
        }
    ])

    assert guidance["state"] == "competing-assessments"
    assert guidance["next_action"] == "inspect-competing-heads"
    assert guidance["competing_count"] == 1


def test_recorded_assessments_are_not_promoted_to_verification():
    guidance = project_advisory_guidance([
        {
            "requires_review": False,
            "current_assessment": {"status": "not-affected"},
        }
    ])

    assert guidance["state"] == "assessments-recorded"
    assert guidance["semantics"]["recorded_assessment_is_verification"] is False
    assert guidance["semantics"]["changed_implies_invalid"] is False
    assert guidance["semantics"]["stale_implies_false"] is False
