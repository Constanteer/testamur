"""Canonical authority compromise reachability.

The implementation lives in ``authority_reachability_v2`` so the legacy tuple-budget
engine cannot silently reintroduce connectivity-as-permission or drop capability
constraints.  This module remains the stable public import surface.
"""

from .authority_reachability_v2 import (
    AuthorityReachabilityClass,
    CompromiseModel,
    authority_blast_radius,
    authority_reachability,
)

__all__ = [
    "CompromiseModel",
    "AuthorityReachabilityClass",
    "authority_reachability",
    "authority_blast_radius",
]
