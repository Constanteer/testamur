# Testamur release readiness

This document is the executable-readiness checklist for the current Testamur convergence/transition line. It does not define a second semantic substrate; canonical semantics remain owned by the `testamur` stores and W2-W5 engines.

## Landed baseline

The Testamur 0.1 convergence/repository-transition baseline is landed on `main`.

- PR #171 merged the final candidate.
- PR #172 was absorbed before that merge.
- candidate head `250bd3656605b17c3a34ab22a3634f38d2276822` passed syntax-check #1989 and release-gate #2126;
- `main` merge commit `434447294478783a1fa55238d9eae3c6f1126bb3` passed post-merge release-gate #2127.

Future release claims must still validate their own exact checkout; the 0.1 evidence above does not certify later post-0.1 changes.

## Executable release gate

Preferred local entrypoint:

```bash
bash scripts/testamur_local_gate.sh release
```

Equivalent release script:

```bash
bash scripts/testamur_release_gate.sh
```

The gate compiles the shipped Testamur package plus canonical `mathhub.py`, audits the production/package namespace and transition boundary, verifies that the required W1-W5 release-e2e files still exist, and then runs the complete current `tests/test_testamur_*.py` regression suite. Fresh-install, ProductService, Web, namespace-migration, historical-reopen, temporal, Policy/Reliance, WorkSession, lineage and affectedness coverage are therefore release-blocking on the exact checkout.

The local entrypoint stamps its log with the Git `HEAD`, tracked-tree state, and selected mode. `release` mode rejects a dirty tracked checkout so a successful release log identifies an exact commit; exported source trees remain testable but report `head=unavailable` and are not a substitute for exact-head release evidence.

GitHub Actions may invoke the same scripts, but **Actions is execution transport, not the release contract**. Missing workflows, deleted workflows, queued jobs, runner starvation, or infrastructure failures that occur before repository code executes do not block ongoing cleanup and do not count as test evidence. Use the local gate instead and record the exact checkout.

Do not call unexecuted CI green. Do not call infrastructure-unavailable CI a product failure.

## Semantic boundaries

The following remain mandatory throughout the gate:

- recorded is not verified;
- fetched/exposed is not relied;
- changed is not invalid;
- stale is not false;
- `recorded_at`, publication provenance, and effective time are distinct;
- `KNOWN_AT`, `AVAILABLE_BY`, and `EFFECTIVE_AT` are distinct temporal clauses;
- lineage propagation is not an affectedness/vulnerability verdict.

## Production distribution boundary

`pyproject.toml` ships only `testamur*` and exposes Testamur-owned entrypoints (`testamur`, `testamur-web`).

`testamur.release_gate.audit_release_surface()` rejects:

- reverse `testamur -> witness` imports;
- legacy Witness package patterns;
- legacy Witness CLI entrypoints;
- `witness/` or `witness_service/` runtime trees in the release checkout;
- Testamur release tests that import the retired Witness runtime;
- a canonical `mathhub.py` server that still imports the retired Witness runtime.

That final MathHub check matters during the shared-repository transition: deleting Witness must not make the retained MathHub product fail at import time.

The fresh-install gate additionally requires the retired Witness packages to be absent from the installed Testamur distribution.

The namespace scanner and its pinned release-critical regression tests cover both retired roots, `witness` and `witness_service`, including static imports and literal dynamic imports. A service-package reverse edge is therefore release-blocking even though `witness_service` is not a `witness.*` submodule.

## MathHub transition boundary

MathHub remains its own product and ontology. Its canonical server, registry, Lean proof graph, and product documentation may coexist in this transition repository while the split is prepared, but they must not depend on the removed Witness runtime and must not become hidden Testamur semantic owners.

The root README, `ARCHITECTURE.md`, and `docs/MATHHUB_PRODUCT.md` are the current presentation boundary for that coexistence. The old MathLab/Witness parent-architecture description and active worker-prompt wave have been retired from the current tree.

## Latest-main reconciliation

The two commits that were previously unique to `main` only revised the superseded autonomous-worker choreography. Their ancestry has now been merged into the convergence branch while retaining the newer post-convergence `PARALLEL.md` and worker-prompt historical notices.

At this checkpoint PR #171 is no longer behind `main`. Re-run the comparison immediately before final merge only to catch any newly-arrived substantive mainline change.

## Hosted boundary

Hosted may remain closed source for authentication, billing, private persistence, scheduling, notification delivery, managed connectors, and hosted deployment concerns. Hosted must consume canonical Testamur identities, records, relations, temporal clauses, policy/reliance decisions, affectedness conclusions, and explanations. Hosted must not maintain a second truth, provenance, reliance, temporal, or affectedness model.

## 0.1 release closure

There are no remaining blockers for the 0.1 local/core convergence baseline: exact-head candidate validation, structural boundary checks, main reconciliation, merge, and the post-merge main release gate have all completed successfully.

Post-0.1 feature branches must establish fresh validation after they are clean-forwarded onto current `main`; do not reuse the 0.1 gate as evidence for Gateway/privacy/hosted changes.

## Explicitly not blockers for the private transition head

- GitHub Actions being absent, queued, deleted, or runner-starved;
- selecting the final open-source license before the public repository split;
- hosted billing/account infrastructure;
- post-0.1 Source Gateway/Codex/private-upload/retention/hosted-sync stacks;
- making MathHub and Testamur share one ontology or runtime.

The current `Proprietary` package metadata is therefore intentional during the private transition. The public license choice becomes a required release decision when the public Testamur repository boundary is created; cleanup automation must not silently choose it.

W1/convergence is complete for the landed 0.1 baseline. Future changes reopen only the scopes they modify and require fresh exact-head evidence.
