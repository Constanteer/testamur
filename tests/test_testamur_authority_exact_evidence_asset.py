from __future__ import annotations

from pathlib import Path


ASSET = Path(__file__).parents[1] / "testamur" / "web" / "authority_reason_groups.js"


def test_exact_evidence_renderer_preserves_path_vs_supporting_roles():
    source = ASSET.read_text(encoding="utf-8")
    assert "renderExactEvidenceRecord" in source
    assert "renderExactEvidenceCollection" in source
    assert "data-evidence-role" in source
    assert "supporting_evidence" in source
    assert "authority_path" in source
    assert "Supporting credential / token evidence" in source
    assert "Traversed authority edge" in source


def test_exact_evidence_renderer_only_projects_recorded_constraint_semantics():
    source = ASSET.read_text(encoding="utf-8")
    assert "renderRecordedConstraintSemantics(record" in source
    assert "recorded does not mean valid" in source
    assert "omitted does not mean unrestricted" in source
    # Presentation must not become a graph/authorization evaluator.
    assert "findPath" not in source
    assert "shortestPath" not in source
    assert "item.constraints" not in source
    assert "lineage" in source  # only in the explicit non-inference module contract


def test_supporting_evidence_is_not_promoted_by_connectivity():
    source = ASSET.read_text(encoding="utf-8")
    assert "supporting evidence never" in source
    assert "becomes an authority-path edge" in source


def test_trust_boundary_renderer_consumes_only_projected_crossings():
    source = ASSET.read_text(encoding="utf-8")
    assert "renderTrustBoundaryCrossing" in source
    assert 'data-crossing-source="recorded-path-edge"' in source
    assert "crossing.boundary_ref" in source
    assert "crossing.trust_boundary_ref" in source
    assert "crossing.edge_id" in source
    assert "crossing.path_index" in source
    assert "browser never derives a crossing" in source
