"""Testamur canonical package.

The ``witness`` namespace is migration compatibility only. New production code
must use ``testamur``; historical storage and wire identifiers may remain stable
without requiring the legacy Python package as the implementation owner.

Authority consumers should use the canonical package-level reachability and
blast-radius entry points. They preserve exact recorded authority paths and do
not infer permissions from material lineage, reliance, affectedness, or graph
connectivity.
"""

from .authority_blast_engine import canonical_authority_blast_radius
from .authority_reachability_engine import canonical_authority_reachability
from . import authority_reachability_v2 as _authority_reachability_v2
from .store_lifecycle import install_store_connection_lifecycle

__version__ = "0.3.0.dev0"

authority_reachability = canonical_authority_reachability
authority_blast_radius = canonical_authority_blast_radius

# Compatibility boundary: importing ``testamur.authority_reachability_v2`` first
# still executes this package initializer before Python returns the submodule.
# Rebind the historical blast-radius symbol so legacy direct imports cannot
# bypass canonical exact-path, seed, model, observation-time, and compromise
# provenance semantics.  Keep the legacy reachability implementation available
# as the low-level traversal used by the canonical reachability projection.
_authority_reachability_v2.authority_blast_radius = canonical_authority_blast_radius

install_store_connection_lifecycle()

__all__ = [
    "__version__",
    "authority_reachability",
    "canonical_authority_reachability",
    "authority_blast_radius",
    "canonical_authority_blast_radius",
]
