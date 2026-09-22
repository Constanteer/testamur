from testamur.authority_blast_engine import canonical_authority_blast_radius
from testamur.authority_reachability_v2 import authority_blast_radius as legacy_authority_blast_radius


def test_legacy_blast_symbol_delegates_to_canonical_engine() -> None:
    """A direct legacy import must not expose the old weak aggregation path."""
    assert legacy_authority_blast_radius is canonical_authority_blast_radius
