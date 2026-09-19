from __future__ import annotations

from typing import Any, Mapping, Sequence

from .authority import AuthoritySubjectKind, TestamurAuthorityStore
from .authority_import import exact_evidence, record_connector_delegation

# GitHub permission levels are provider semantics, not generic Testamur actions.
# Keep this mapping deliberately closed: a new provider value must be reviewed before
# it can create authority in the canonical graph.
_GITHUB_LEVEL_ACTIONS: dict[str, tuple[str, ...]] = {
    "read": ("read",),
    "write": ("read", "write"),
}


def github_permission_capabilities(
    permissions: Mapping[str, Any],
    *,
    installation_id: str,
    repository_refs: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Translate an observed GitHub App/OAuth permission set without widening it.

    ``permissions`` is the exact provider permission object. Unknown levels fail
    closed. Repository selection is retained as a constraint; absence of a repository
    list is unresolved rather than interpreted as all repositories.
    """
    if not isinstance(permissions, Mapping) or not permissions:
        raise ValueError("GitHub connector permissions must be a non-empty object")
    installation = str(installation_id).strip()
    if not installation:
        raise ValueError("installation_id must be a non-empty string")

    repos = sorted({str(ref).strip() for ref in (repository_refs or ()) if str(ref).strip()})
    result: list[dict[str, Any]] = []
    for permission, raw_level in sorted(permissions.items(), key=lambda item: str(item[0])):
        name = str(permission).strip()
        level = str(raw_level).strip().lower()
        if not name:
            raise ValueError("GitHub permission name must be non-empty")
        actions = _GITHUB_LEVEL_ACTIONS.get(level)
        if actions is None:
            raise ValueError(f"unsupported GitHub permission level: {raw_level!r}")
        for action in actions:
            constraints: dict[str, Any] = {
                "provider": "github",
                "installation_id": installation,
                "provider_permission": name,
                "provider_level": level,
            }
            if repos:
                constraints["repository_refs"] = repos
            else:
                constraints["repository_selection"] = "unresolved"
            result.append(
                {
                    "namespace": "github",
                    "action": action,
                    "resource": name,
                    "constraints": constraints,
                }
            )
    return result


def record_github_connector_permissions(
    store: TestamurAuthorityStore,
    *,
    delegator_ref: str,
    connector_ref: str,
    installation_id: str,
    permissions: Mapping[str, Any],
    evidence_ref: str,
    evidence_revision: str,
    repository_refs: Sequence[str] | None = None,
    boundary_refs: Sequence[str] | None = None,
    observed_at: str | None = None,
    analyzer: str = "testamur.github-authority-adapter",
    analyzer_version: str = "1",
) -> dict[str, Any]:
    """Record exact GitHub connector delegation from one pinned provider snapshot.

    Merely observing an installation never creates authority. All permission and
    evidence inputs are validated before the store is mutated, so malformed provider
    data cannot leave a connector subject that appears authoritative by adjacency.
    """
    connector = str(connector_ref).strip()
    if not connector:
        raise ValueError("connector_ref must be a non-empty string")
    capabilities = github_permission_capabilities(
        permissions,
        installation_id=installation_id,
        repository_refs=repository_refs,
    )
    evidence = exact_evidence(
        ref=evidence_ref,
        revision=evidence_revision,
        evidence_class="DERIVED",
        analyzer=analyzer,
        analyzer_version=analyzer_version,
        observed_at=observed_at,
    )
    store.record_subject(
        AuthoritySubjectKind.CONNECTOR,
        label=f"GitHub connector {installation_id}",
        subject_ref=connector,
        attributes={"provider": "github", "installation_id": str(installation_id)},
    )
    return record_connector_delegation(
        store,
        delegator_ref=delegator_ref,
        connector_ref=connector,
        capabilities=capabilities,
        evidence=[evidence],
        constraints={"provider": "github", "installation_id": str(installation_id)},
        boundary_refs=boundary_refs,
    )
