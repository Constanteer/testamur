"""Testamur canonical package.

The ``witness`` namespace is migration compatibility only. New production code
must use ``testamur``; historical storage and wire identifiers may remain stable
without requiring the legacy Python package as the implementation owner.

Authority blast-radius consumers should use :func:`authority_blast_radius` from
this canonical package surface.  It is intentionally wired to the provenance-
preserving orchestration rather than the legacy reachability-module aggregator:
each explicit compromise seed is traversed independently at one observation
instant and only engine-recorded authority is aggregated afterwards.  Material
lineage, reliance, affectedness, or graph connectivity never grant authority.
"""

from .authority_blast_engine import canonical_authority_blast_radius
from .store_lifecycle import install_store_connection_lifecycle

__version__ = "0.3.0.dev0"

# Canonical public entry point. Keep the implementation's longer name available
# for callers that want to be explicit, while making the safe orchestration the
# default package-level authority blast API.
authority_blast_radius = canonical_authority_blast_radius

# Keep the historical graph-store resource semantics when consumers enter through
# the canonical namespace.  This is idempotent and imports no legacy package.
install_store_connection_lifecycle()

__all__ = [
    "__version__",
    "authority_blast_radius",
    "canonical_authority_blast_radius",
]
