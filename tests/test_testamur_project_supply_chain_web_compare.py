from pathlib import Path


def test_project_supply_chain_surface_hydrates_latest_mechanical_diff():
    js = (Path(__file__).parents[1] / "testamur" / "web" / "supply-chain-guidance.js").read_text()
    assert "/v1/project?ref=" in js
    assert "data.liveSupplyChainCompare" in js or "dataset.liveSupplyChainCompare" in js
    assert "LATEST COMPARISON" in js
    assert "upgrade != safe" in js
    assert "downgrade != vulnerable" in js
    assert "changed != invalid" in js
    assert "diff?.dependencies?.changed" in js


def test_project_review_surface_attaches_mechanical_diff_without_trust_score():
    source = (Path(__file__).parents[1] / "testamur" / "project_review_surface.py").read_text()
    assert "diff_project_supply_chain(" in source
    assert "to_scan_revision_id=scan_revision_id or None" in source
    assert '"latest_binding_scan_diff_is_mechanical": True' in source
    assert '"version_direction_implies_safety": False' in source
    assert '"generic_trust_score_used": False' in source
