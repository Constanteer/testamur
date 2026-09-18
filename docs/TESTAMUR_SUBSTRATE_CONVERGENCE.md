# Testamur substrate convergence

Status: **post-retirement substrate compatibility contract**.

`testamur` is the only active Testamur production/runtime namespace. Historical Witness storage, wire identifiers, and legacy object references may remain as compatibility inputs; no importable Witness runtime/shim is required or supported by the converged release line.

## Dependency rule

The current boundary is:

```text
historical persisted data / references
        ↓
Testamur compatibility readers / projection adapters
        ↓
canonical Testamur implementation
```

Forbidden active edges:

```text
testamur -> witness
new caller -> witness compatibility package
MathHub -> witness runtime
```

The structural release audit and the complete Testamur regression suite enforce these boundaries.

## Keep two ObjectKind vocabularies distinct

`testamur.contracts.ObjectKind` names durable public object families such as `record`, `policy`, `reliance`, and `run`.

`testamur.model.ObjectKind` preserves the semantic graph-role vocabulary such as `claim`, `evidence`, and `artifact`.

They are not interchangeable. Namespace convergence must not silently change semantics.

## Identity rules

New Testamur durable/runtime objects use Testamur-owned identities. In particular, new runtime runs use `tst:run:*`; historical `wtn:run:*` references remain readable only for compatibility.

Legacy object projection uses the shared rule in `testamur.substrate_bridge`:

```text
identity = (identity_version, source_namespace, source_ref)
identity -> deterministic tst:<kind>:<hash>
```

The source namespace is provenance input. It does not make the legacy namespace a runtime owner.

Historical random IDs such as `wrr_<hex>` and `wap_<hex>` are read/projection compatibility references, not the default identity scheme for new Testamur writes.

`testamur.legacy_adapter.resolve_reference()` classifies canonical `tst:*`, historical `wtn:*`, historical random IDs, and opaque external references without asserting existence, validity, verification, reliance, or authority.

## Projection semantics

`BridgeEnvelope` preserves canonical ref, original namespace/ref, source schema, payload, and provenance.

Projection is identity/provenance transport only. It never promotes verification, truth, authority, currentness, or reliance.

Projection comparison remains explicit:

```text
IDENTICAL
DIFFERENT_IDENTITY
SAME_IDENTITY_CHANGED
ORIGIN_CONFLICT
```

The same identity with changed payload/provenance is **not** silently idempotent. `reconcile_legacy_projection()` fails closed unless a caller explicitly accepts a same-origin revision. Different origins claiming the same canonical identity remain a conflict.

## Physical persistence compatibility

Implementation ownership is under `testamur`. Historical physical names may remain only where changing them would break durable data.

| Historical persistence/wire surface | Canonical owner | Compatibility policy |
| --- | --- | --- |
| runtime protocol/events | `testamur.runtime_protocol` / `runtime_integrity` | historical `wtn:*` records readable; new writes use Testamur protocol/IDs |
| runtime SQLite tables | `testamur.runtime_store*` | `witness_runtime_*` physical names may remain |
| semantic graph schema token | `testamur.model` | historical hash/schema token may remain |
| append-oriented graph store | `testamur.store.TestamurStore` | historical `witness_*` physical tables/read IDs may remain |
| revision DAG + CAS/snapshots | `testamur.revision_store*` / `TestamurVersionedStore` | hash-participating historical CAS/snapshot tokens may remain |
| relation lifecycle snapshots | `testamur.revision_relations` | historical retraction storage may remain |
| assurance snapshot extension | `testamur.revision_assurance` | historical assurance snapshot token may remain |

No public canonical class needs to be named `WitnessStore`, and no historical import path is required to reopen persisted data.

A physical table/token rename is a separate migration project: it must be transactional/versioned and prove historical databases/content addresses still reopen identically. Cosmetic string replacement is forbidden.

## Landed domain ownership

Worker branches are no longer semantic owners. The converged line owns:

- W1/core evidence, package/release boundary, ProductService composition;
- W2 temporal semantics;
- W3 Policy / Assessment / Reliance;
- W4 WorkSession / reconciliation;
- W5 lineage / advisory / affectedness.

The current ownership map is `docs/TESTAMUR_CONVERGENCE.md`.

Post-0.1 agent/Gateway/privacy/hosted stacks must consume these owners rather than reintroduce parallel semantic engines.

## Import inventory

`testamur.convergence.scan_legacy_imports(root)` and `legacy_import_report(root)` remain useful machine-readable inventory tools for static and literal dynamic imports.

For the release candidate, however, the target is no longer “ready to delete Witness later”: the runtime/package trees are already retired. Any active canonical/Testamur-test/MathHub entrypoint import of Witness is a regression.

## Release invariants

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
lineage != affectedness verdict
```

Run the exact-head release contract with:

```bash
bash scripts/testamur_local_gate.sh release
```

The gate verifies required W1-W5 semantic test files exist and runs the complete current `tests/test_testamur_*.py` suite. GitHub Actions may transport this gate but does not define it.
