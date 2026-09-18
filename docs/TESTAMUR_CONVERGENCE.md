# Testamur convergence map

This document is the canonical ownership map for the Testamur 0.1 local/core convergence line.

It exists to prevent branch history from becoming semantic ownership. A worker branch may contain useful implementation history, but only the owners below define the current runtime contract.

## Completion scope

Repository/product closure is defined by `docs/TESTAMUR_COMPLETION_SPEC.md`. This convergence map owns semantic/runtime ownership; the completion spec owns the end-state repository split, Witness retirement requirements, OSS/hosted boundaries, Web/product closure, deployment, billing/legal shells, and the definition of done. Older worker notes must not override either document.

## Landed release line

The 0.1 semantic convergence and repository-boundary transition are landed on `main`.

- PR #171 landed the final convergence candidate.
- PR #172 was absorbed into #171 before #171 landed.
- post-merge `testamur-release-gate` #2127 succeeded on merge commit `434447294478783a1fa55238d9eae3c6f1126bb3`.

Do not revive older W1-W5 integration, Web, temporal-front-door, or Source-capture branches as semantic owners. Distinct future work must clean-forward onto current `main`.

## Runtime ownership

### W1 / core evidence substrate

Owns the local Testamur environment, receipt/evidence graph, verification, canonical object contracts, release boundary, front router, ProductService integration boundary, and structural namespace gate.

The shipped Python namespace is `testamur*`. Production `testamur -> witness` imports are forbidden.

### W2 / temporal

Canonical temporal ownership is the later W2 model/store/query implementation already present in convergence:

- `temporal_model.py`
- `temporal_store.py`
- `temporal_query.py`

Public product reads expose explicit `KNOWN_AT`, `AVAILABLE_BY`, and `EFFECTIVE_AT` modes. No generic ambiguous `as_of` alias should collapse those meanings.

### W3 / policy and reliance

The convergence head uses the latest W3 owner implementations, including post-W1 hardening:

- `assessment.py`
- `assessment_projection.py`
- `policy.py`
- `policy_comparison.py`
- `reliance.py`
- `reliance_basis.py`
- `reliance_bridge.py`
- `reliance_neighborhood.py`
- `reliance_projection.py`
- `reliance_status.py`

Policy identity is versioned and immutable. Reliance records exact frozen basis. `fetched != relied`, `stale != false`, and unavailable current evidence must not erase historical reliance.

### W4 / WorkSession and reconciliation

The convergence head uses the latest W4-owned runtime files:

- `_work_session_reconciliation.py`
- `_work_session_types.py`
- `agent_capture.py`
- `agent_protocol.py`
- `reconciliation.py`
- `reconciliation_recovery.py`
- `work_session.py`

Only explicit reconciliation may promote durable reliance. Observation, exposure, fetch, and agent visibility do not imply reliance.

### W5 / lineage and affectedness

The convergence head uses the latest W5 lineage/affectedness owner family:

- `advisory.py`
- `advisory_adapters.py`
- `advisory_resolution.py`
- `affectedness.py`
- `affectedness_conflicts.py`
- `affectedness_explain.py`
- `affectedness_integrity.py`
- `affectedness_scope.py`
- `affectedness_supersession.py`
- `component_identity.py`
- `lineage.py`
- `lineage_projection.py`
- `vendor_lineage.py`

The W5-to-reliance integration uses the later W3 `reliance_bridge.py` policy-basis filtering, not the older W5-local hook behavior.

Lineage is structural evidence. It does not itself manufacture an affectedness, validity, or truth verdict.

## Product/Web boundary

`TestamurProductService` is the canonical local product read boundary.

The Web server and browser UI are projections over ProductService. Web code must not own a second Store, Policy engine, Reliance engine, temporal model, or affectedness model.

The current workspace dashboard presents tracked Sources as user-facing "projects" for navigation. `Project` is not a second durable ontology.

Older W4 read-service / Public API / W5 Web stacks are historical reference only. Useful UX ideas such as catalogs, compare views, and write flows may be rebuilt on this boundary, but their old backend architecture is retired.

## Source acquisition boundary

The older W3 general CLI HTTP fetch/capture path is retired as canonical architecture.

Exact source acquisition belongs to the explicit Source Gateway line (currently PR #156), which should be clean-forwarded/rebased onto the landed convergence core. Host plugins should consume the Gateway rather than reimplement network capture semantics.

## Post-0.1 stacks

These remain separate from the 0.1 convergence candidate and should be clean-forwarded/rebased after PR #171 lands:

- W6 agent workflow extensions beyond the converged WorkSession core
- Source Gateway
- Codex + Source Gateway integration
- private upload / retention / erasable metadata
- hosted agent sync

Their account, privacy, transport, plugin, and hosted concerns must compose around the evidence semantics above; they may not redefine them.

## Repository boundary

The transition repository currently still carries MathHub-era/product material while the Testamur runtime/package boundary is being isolated. The release package, CLI, Web entrypoint, and canonical runtime are Testamur-owned; historical or separate MathHub material must not be mistaken for Testamur semantic ownership.

The intended split remains:

```text
public Testamur core / CLI
public integrations / tool adapters
private hosted / account / billing / service plane
MathHub retained as its own product/history rather than a hidden second Testamur runtime
```

Do not solve the split by copying hosted/account/billing semantics into the open-source core.

## Release invariants

The release line preserves these distinctions:

- recorded != verified
- fetched != relied
- changed != invalid
- stale != false
- lineage != affectedness verdict
- upload != publication rights
- hosted != trusted
- paid != verified
- `KNOWN_AT != AVAILABLE_BY != EFFECTIVE_AT`

The target local closure is:

`SourceRevision -> WorkSession -> explicit reconciliation -> Policy -> Reliance -> Watch/change -> impact/affectedness -> revalidation`

## Release validation policy

GitHub Actions is a transport for checks, not a semantic or release dependency.

If Actions are missing, deleted, queued, runner-starved, or fail before executing repository code, continue the release process with the repository-local gate:

```bash
bash scripts/testamur_local_gate.sh release
```

A local gate may be treated as authoritative only for the exact checkout on which it ran. An unexecuted CI job is neither green nor a blocker; record it as infrastructure-unavailable/unexecuted.

The structural release audit must also remain clean:

- only `testamur*` is shipped;
- no `witness` / `witness_service` runtime trees in the release checkout;
- no production Testamur import back into Witness;
- no Testamur tests depending on retired Witness runtime modules.

## 0.1 closure state

The 0.1 local/core convergence is closed on `main`: exact-head candidate gates passed before merge, the post-merge main release gate passed, the structural namespace boundary is clean, and the retired Witness runtime is no longer a shipped dependency.

Remaining work is post-0.1 product/repository work: Source Gateway/Codex integration, private upload/retention/metadata, hosted sync/service-plane separation, repository extraction, and the eventual public-license decision.

GitHub Actions availability remains execution infrastructure rather than a semantic requirement.
