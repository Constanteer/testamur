"""Testamur canonical package.

The ``witness`` namespace is migration compatibility only. New production code
must use ``testamur``; historical storage and wire identifiers may remain stable
without requiring the legacy Python package as the implementation owner.
"""

from . import project_store as _project_store
from .project_review_surface import project_with_advisory_reviews
from .store_lifecycle import install_store_connection_lifecycle

__version__ = "1.0.0"

# Repository-binding identifiers are package-owned stable storage identifiers.
# Keep these assignments here until project_store's next schema edit can inline
# them without rewriting unrelated storage code.
_project_store.REPOSITORY_BINDING_PREFIX = "rpb_"
_project_store.REPOSITORY_BINDING_REVISION_PREFIX = "rpbr_"
_project_store._REPOSITORY_BINDING_KINDS = {"local-path", "git"}

# Keep the historical graph-store resource semantics when consumers enter through
# the canonical namespace. This is idempotent and imports no legacy package.
install_store_connection_lifecycle()

__all__ = ["__version__", "project_with_advisory_reviews"]
