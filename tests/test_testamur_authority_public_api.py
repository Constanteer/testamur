from __future__ import annotations


def test_package_authority_blast_radius_uses_canonical_orchestration() -> None:
    import testamur
    from testamur.authority_blast_engine import canonical_authority_blast_radius
    from testamur.authority_reachability_v2 import authority_blast_radius as legacy_authority_blast_radius

    assert testamur.authority_blast_radius is canonical_authority_blast_radius
    assert testamur.authority_blast_radius is not legacy_authority_blast_radius


def test_package_exports_canonical_authority_blast_surface() -> None:
    import testamur

    assert "authority_blast_radius" in testamur.__all__
    assert "canonical_authority_blast_radius" in testamur.__all__
