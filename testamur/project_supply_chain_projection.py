from __future__ import annotations

import json
from typing import Any

from .advisory_project_lookup import project_advisory_revisions_for_upstream_refs


def _repository_binding(statement: dict[str, Any]) -> dict[str, str] | None:
    raw = statement.get("repository_binding")
    if not isinstance(raw, dict): return None
    binding_id = str(raw.get("binding_id") or "").strip(); binding_key = str(raw.get("binding_key") or "").strip(); binding_revision_id = str(raw.get("binding_revision_id") or "").strip()
    if not binding_id or not binding_key or not binding_revision_id: return None
    return {"binding_id": binding_id, "binding_key": binding_key, "binding_revision_id": binding_revision_id}


def _project_scan_projection(service: Any, *, record: dict[str, Any], revision: dict[str, Any], statement: dict[str, Any]) -> dict[str, Any]:
    manifest_revision_ids = [str(v) for v in statement.get("manifest_revision_ids") or [] if isinstance(v, str) and v]
    dependency_revision_ids = [str(v) for v in statement.get("dependency_record_revision_ids") or [] if isinstance(v, str) and v]
    manifests = []
    for revision_id in manifest_revision_ids[:200]:
        item = service.records.get_revision(revision_id)
        if item is None: continue
        try: payload = json.loads(str(item.get("statement") or "{}"))
        except json.JSONDecodeError: continue
        if payload.get("schema") != "testamur.supply-chain.manifest.v1": continue
        deps = payload.get("dependency_revision_ids")
        manifests.append({"record_id": item.get("record_id"), "record_revision_id": revision_id, "recorded_at": item.get("recorded_at"), "path": payload.get("path"), "parser": payload.get("parser"), "sha256": payload.get("sha256"), "dependency_count": len(deps) if isinstance(deps, list) else 0})
    dependencies = []; component_revision_ids: set[str] = set()
    for revision_id in dependency_revision_ids[:1000]:
        item = service.records.get_revision(revision_id)
        if item is None: continue
        try: payload = json.loads(str(item.get("statement") or "{}"))
        except json.JSONDecodeError: continue
        if payload.get("schema") != "testamur.supply-chain.dependency.v1": continue
        component_revision = payload.get("component_revision")
        if not isinstance(component_revision, dict): continue
        component = component_revision.get("component"); component = component if isinstance(component, dict) else {}
        component_revision_id = str(component_revision.get("component_revision_id") or "").strip()
        if component_revision_id: component_revision_ids.add(component_revision_id)
        observed_in = payload.get("observed_in")
        dependencies.append({"record_id": item.get("record_id"), "record_revision_id": revision_id, "recorded_at": item.get("recorded_at"), "component_revision_id": component_revision_id or None, "component_id": component.get("component_id"), "ecosystem": component.get("namespace"), "name": component.get("name"), "version": component_revision.get("version"), "digest": component_revision.get("digest"), "locator": component_revision.get("locator"), "identity_strength": component_revision.get("identity_strength"), "is_exact_revision": bool(component_revision.get("is_exact_revision")), "direct": payload.get("direct"), "observed_in": list(observed_in) if isinstance(observed_in, list) else []})
    dependencies.sort(key=lambda x: (str(x.get("ecosystem") or ""), str(x.get("name") or ""), str(x.get("version") or ""))); manifests.sort(key=lambda x: str(x.get("path") or ""))
    advisory_candidates = []
    advisory_revisions, unresolved_advisory_count = project_advisory_revisions_for_upstream_refs(service.advisories, component_revision_ids)
    for advisory_revision in advisory_revisions:
        upstream_refs = {str(v) for v in advisory_revision.get("upstream_refs") or [] if str(v)}; matched = sorted(component_revision_ids & upstream_refs)
        event = service.advisories.get_event(str(advisory_revision.get("event_id") or "")) or {}
        advisory_candidates.append({"event_id": advisory_revision.get("event_id"), "event_revision_id": advisory_revision.get("event_revision_id"), "provider": event.get("provider"), "external_id": event.get("external_id"), "event_class": advisory_revision.get("event_class"), "issued_at": advisory_revision.get("issued_at"), "severity": dict(advisory_revision.get("severity") or {}), "matching_component_revision_ids": matched, "status": "exact_identity_overlap", "semantics": {"exact_identity_overlap_is_affectedness_verdict": False, "applicability_assessment_required": True}})
    binding = _repository_binding(statement)
    return {"scan_record_id": record["record_id"], "scan_revision_id": revision["revision_id"], "recorded_at": revision.get("recorded_at"), "repository_binding": binding, "manifest_count": len(manifest_revision_ids), "dependency_count": len(dependency_revision_ids), "component_revision_count": len(component_revision_ids), "manifests": manifests, "dependencies": dependencies, "inventory_truncated": len(manifest_revision_ids) > len(manifests) or len(dependency_revision_ids) > len(dependencies), "warnings": list(statement.get("warnings") or []), "advisory_candidates": advisory_candidates, "advisory_candidate_count": len(advisory_candidates), "unresolved_advisory_count": unresolved_advisory_count, "semantics": {**dict(statement.get("semantics") or {}), "supply_chain_scope_is_repository_binding": binding is not None, "missing_repository_binding_provenance_is_not_inferred": True, "advisory_candidate_requires_exact_upstream_ref_overlap": True, "advisory_candidate_is_not_affectedness_verdict": True, "unresolved_identity_is_not_fuzzy_matched": True}}


def project_supply_chain_projections(service: Any, project_id: str) -> list[dict[str, Any]]:
    """Return newest immutable observation per binding, newest binding first."""
    projections = []; seen_binding_ids: set[str] = set(); legacy_added = False
    with service.records.connect() as conn:
        rows = conn.execute("""
            SELECT rec.record_json AS record_json, rev.record_json AS revision_json
            FROM testamur_relations AS rel
            JOIN testamur_record_revisions AS rev ON rev.revision_id = rel.to_ref
            JOIN testamur_records AS rec ON rec.record_id = rev.record_id
            WHERE rel.from_ref = ? AND rel.relation_type = 'cites' AND rec.record_kind = 'supply-chain-scan'
            ORDER BY rev.recorded_at DESC, rev.revision_id DESC
        """, (str(project_id),)).fetchall()
    for row in rows:
        record = json.loads(str(row["record_json"])); revision = json.loads(str(row["revision_json"]))
        try: statement = json.loads(str(revision.get("statement") or "{}"))
        except json.JSONDecodeError: continue
        if statement.get("schema") != "testamur.supply-chain.project-scan.v1": continue
        binding = _repository_binding(statement)
        if binding is None:
            if legacy_added: continue
            legacy_added = True
        else:
            binding_id = binding["binding_id"]
            if binding_id in seen_binding_ids: continue
            seen_binding_ids.add(binding_id)
        projections.append(_project_scan_projection(service, record=record, revision=revision, statement=statement))
    return projections
