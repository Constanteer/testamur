from pathlib import Path


WEB = Path(__file__).parents[1] / "testamur" / "web"
GUIDE = (WEB / "contextual-guide.js").read_text(encoding="utf-8")
INDEX = (WEB / "index.html").read_text(encoding="utf-8")


def test_contextual_guide_is_loaded_and_teaches_canonical_review_loop():
    assert '/contextual-guide.js' in INDEX
    assert '/contextual-guide.css' in INDEX
    for label in ('Source', 'Revision', 'Compare', 'Impact', 'Revalidation'):
        assert label in GUIDE
    assert 'REVIEW WORKFLOW' in GUIDE
    assert 'Why these steps?' in GUIDE


def test_contextual_guide_preserves_semantic_boundaries():
    for boundary in (
        'recorded ≠ verified',
        'fetched ≠ relied',
        'changed ≠ invalid',
        'stale ≠ false',
    ):
        assert boundary in GUIDE
    lowered = GUIDE.lower()
    assert 'trust score' not in lowered
    assert 'confidence score' not in lowered
    assert 'infer verification' in lowered
    assert 'explicit recorded reliance' in lowered


def test_contextual_guide_ignores_its_own_dom_mutations():
    assert 'function onlyGuideMutations(records)' in GUIDE
    assert 'if (onlyGuideMutations(records)) return;' in GUIDE
    assert 'queueMicrotask(() => {' in GUIDE
    assert 'queueRender();' in GUIDE


def test_impact_cards_expose_recorded_provenance_without_claiming_affectedness():
    # The Impact enhancement may only surface provenance supplied by the
    # provider. Missing provenance stays visibly missing rather than being
    # synthesized by the Web layer.
    assert 'Recorded basis' in GUIDE
    assert 'Not supplied by this provider' in GUIDE
    assert 'Inspect basis' in GUIDE
    assert 'Recorded at' in GUIDE

    # A recorded reliance edge explains historical provenance; it is not a
    # conclusion that the selected change affected or invalidated downstream
    # work. Keep that distinction visible in the review card itself.
    assert 'it does not say this change affected or invalidated the downstream work' in GUIDE
