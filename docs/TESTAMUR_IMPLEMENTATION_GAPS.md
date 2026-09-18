# Testamur implementation / release gap matrix

> **Status:** operational tracker for the landed Testamur 0.1 baseline and post-0.1 work. This is not a normative semantics document.
>
> **Current baseline:** `main` through the Testamur public-alpha launch cleanup (`7ee0a099f44f`), with Source Gateway, Codex integration, private Source ingestion/metadata, and reference-aware raw-byte retention already clean-forwarded onto the canonical line. The static public launch surface, legal/pricing pages, and standalone site container are also landed.
>
> **Rule:** GitHub Actions availability is not a product blocker. When hosted/self-hosted Actions are absent, queued, or unavailable, use the repository-local gates and static release audit. Do not mark unexecuted tests green; record them as unexecuted infrastructure checks instead.

This tracker replaces the pre-convergence snapshot that still described now-landed W2/W3/W4/W5 capabilities as `SPEC_ONLY` or as parallel Witness implementations.

## Current status vocabulary

```text
LANDED
  implemented on the canonical Testamur line and owned by `testamur*`

LANDED_LOCAL
  implemented and usable locally, but hosted/service-plane operation is intentionally outside 0.1

STACKED_POST_0_1
  preserved implementation exists only on an older stack and still needs selective clean-forward

CLEAN_FORWARD_PR
  rebuilt on current canonical main and awaiting review/landing

TRANSITIONAL
  correct enough for the private transition repository but still awaiting repository split, naming, packaging, or publication cleanup

OPEN
  not yet implemented or still requires a product/owner decision
```

## Release-critical matrix

| Capability | Current state | Canonical implementation / owner | Remaining work |
|---|---|---|---|
| Testamur package / CLI boundary | **LANDED** | `pyproject.toml`, `testamur.front_router`, release-surface audit | Keep shipped namespace `testamur*`; no production `testamur -> witness` imports |
| Witness runtime/package retirement | **LANDED on main** | compatibility readers inside `testamur`, release audit | Historical `witness_*` SQLite names / old IDs may remain as data inputs; no live package/runtime tree |
| Runtime/wire new-write identity | **LANDED on main** | `runtime_protocol.py`, `runtime_store.py`, `command_execution.py` | New writes use Testamur protocol/ID identity; preserve read-only historical reopen coverage |
| Semantic-model active identity | **LANDED on main** | `model.py`, `test_testamur_model_namespace.py` | Historical `witness-core-v0.1` remains a compatibility token; active validation/error wording is Testamur-owned |
| Revision/CAS compatibility class identity | **LANDED on main** | `revision_store_legacy.py`, `revision_store_v2.py`, store namespace tests | Historical CAS/snapshot tokens remain hash-stable compatibility serialization; active/public class identity is Testamur/neutral legacy, never `WitnessStore` |
| Testamur test namespace gate | **LANDED on main** | `release_gate.py`, `test_testamur_release_gate.py` | `test_testamur_* -> witness` imports are release-blocking, not merely migration debt |
| Test discovery after Witness retirement | **LANDED on main** | `tests/conftest.py`, `tests/run_unittest_suite.py` | Current Testamur/MathHub tests are collected directly; no hidden W7 skip/supersession manifest from the retired runtime |
| Source / Snapshot / SourceRevision | **LANDED** | `source_store.py`, ProductService | None for 0.1 core |
| Record / RecordRevision / Relation | **LANDED** | `record_store.py`, `record_source.py` | Continue relation-domain expansion only when required by a concrete workflow |
| Watch / Evaluation / Alert | **LANDED_LOCAL** | `watch_store.py`, ProductService | Hosted scheduler/worker is post-0.1 service-plane work |
| Mechanical compare / retained bytes | **LANDED_LOCAL** | `blob_store.py`, `mechanical_diff.py` | Hosted retention/account policy remains post-0.1 |
| Temporal `KNOWN_AT` / `AVAILABLE_BY` / `EFFECTIVE_AT` | **LANDED** | `temporal_model.py`, `temporal_store.py`, `temporal_query.py` | Preserve semantic separation; do not collapse into generic `as_of` |
| Purpose-scoped Policy / Assessment | **LANDED** | W3 policy/assessment owner family | No second Web/service policy engine |
| Durable Reliance | **LANDED** | W3 reliance owner family + `reliance_bridge.py` | Reliance must still come only from explicit reconciliation |
| WorkSession + reconciliation | **LANDED** | W4 WorkSession/reconciliation owner family | Product polish only; semantics are release-owned |
| Lineage / advisory / affectedness | **LANDED** | W5 owner family | Continue external advisory adapters and product explanation as post-core expansion |
| Product read boundary | **LANDED** | `TestamurProductService` | Web/API remain thin projections |
| GitHub-like Web workspace | **LANDED on main** | dashboard projection + `testamur/web/*` | Final polish and repository split; no new durable `Project` ontology |
| MathHub retired-runtime independence | **LANDED on main** | `mathhub.py` + release audit | Keep canonical MathHub entrypoint free of retired Witness runtime imports |
| Local release audit | **LANDED** | `testamur.release_gate`, `scripts/testamur_release_gate.sh` | Run locally whenever Actions are unavailable |
| Local compile surface | **LANDED on main** | `scripts/testamur_local_gate.sh` | Smoke/release/full compile the complete shipped `testamur` package plus canonical `mathhub.py`, avoiding stale hand-maintained module lists |
| Optional CI delegation | **LANDED on main** | `.github/workflows/registry-test.yml` | Workflow delegates to `scripts/testamur_local_gate.sh release`; runner availability does not own release semantics |
| Full exact-head Testamur release suite | **LANDED as executable gate** | `scripts/testamur_release_gate.sh` | Gate verifies required W1-W5 release-e2e files exist, then runs the complete current `tests/test_testamur_*.py` suite once; execute it on the exact candidate head |
| Root/current transition docs | **LANDED on main** | `README.md`, `ARCHITECTURE.md`, `QUICK_LAUNCH.md`, `PARALLEL.md`, namespace migration contract | Retired Witness parent-architecture text and old worker-wave prompts are removed from active authority; keep links/status accurate |
| Latest-main reconciliation | **LANDED on main** | `docs/TESTAMUR_RELEASE_READINESS.md` + Git compare | Main ancestry reconciled while preserving newer convergence docs; recheck only for newly-arrived changes immediately before final merge |
| Source Gateway | **LANDED_LOCAL** | `source_fetch.py`, `source_gateway.py`, `source_gateway_mcp.py`, `source_gateway_cli.py` | Keep exact-revision capture separate from durable reliance; hosted egress/auth remains service-plane work |
| Codex exact Source Gateway integration | **LANDED_LOCAL** | `integrations/codex`, `plugins/testamur-codex`, `codex_gateway_hook.py` | Preserve thin-adapter boundary and canonical WorkSession/Source semantics |
| Private file upload / erasable metadata | **LANDED_LOCAL** | `user_file_ingest.py`, `source_access.py`, `private_source_metadata.py` | Owner-private convenience metadata stays outside canonical public DTOs |
| Reference-aware raw-byte retention / purge | **LANDED_LOCAL** | `blob_retention.py`, `source_cli.py`, `docs/TESTAMUR_BLOB_RETENTION.md`; historical #158/#184 closed | Hosted retention administration/replica deletion remains service-plane work; local CLI projection is canonical |
| Public alpha launch surface | **LANDED** | `site/*`, `tests/test_testamur_site_surface.py` | External domain/TLS deployment and a dedicated public support/privacy contact remain operational owner tasks |
| Hosted agent sync | **STACKED_POST_0_1** | historical #159 | Selectively clean-forward into the private hosted/service-plane boundary; do not restore a second core runtime |
| Repository split | **TRANSITIONAL** | repository-boundary layout absorbed from #172 into #171 | Create final public Testamur core/tools repositories and private hosted repository when owner is ready |
| Open-source license | **OPEN owner decision** | `pyproject.toml` is intentionally `Proprietary` during private transition | Choose license only when the public repository boundary is created |

## Canonical 0.1 closure

```text
SourceRevision
  -> WorkSession
  -> explicit reconciliation
  -> Policy
  -> Reliance
  -> Watch/change
  -> impact / affectedness
  -> revalidation
```

The following remain invariants, not feature gaps:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
lineage != affectedness verdict
upload != publication rights
hosted != trusted
paid != verified
KNOWN_AT != AVAILABLE_BY != EFFECTIVE_AT
```

## What is left after 0.1 convergence

The 0.1 local/core convergence is closed on `main`. Exact-head candidate validation succeeded before merge, the structural namespace audit remained clean, and post-merge release gate #2127 succeeded on the actual `main` merge commit.

Current work is post-0.1:

1. deploy the landed static launch surface behind the chosen public domain/TLS edge and publish a dedicated public support/privacy contact;
2. selectively clean-forward the hosted sync transport contract from closed historical #159 behind the private hosted/service-plane boundary;
3. selectively clean-forward any still-useful adapter/attestation/project-scan UX pieces from closed historical #139 without restoring its parallel stores/runtime;
4. keep closed historical stacks (#139, #153, #156, #158, #159, #160, #161, #184) as source material only; do not merge them independently;
5. perform the final public repository split and choose an OSS license only when that public boundary is explicit;
6. before a versioned public package/release tag, reconcile the product milestone naming with the current package version (`0.3.0.dev0`) rather than silently publishing contradictory version identities.

Historical persistence tokens remain compatibility inputs; new writes/public types must remain Testamur-owned.

## Explicitly not blockers for 0.1 local/core

- GitHub Actions being deleted, unavailable, queued, or unable to acquire a runner;
- hosted billing, quotas, customer mapping, or distributed scheduler infrastructure;
- automatic cloud publication;
- a global truth/trust score;
- hidden model cognition / chain-of-thought capture;
- folding post-0.1 Gateway/privacy/hosted stacks into the core before convergence is stable.
