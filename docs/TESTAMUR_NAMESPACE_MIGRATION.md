# Testamur namespace migration

Status: **post-retirement compatibility contract** for the Testamur convergence / repository-boundary line.

## Current state

`testamur` is the only active Python/runtime/CLI namespace for Testamur.

The working tree must not require importable `witness` or `witness_service` packages. Historical Git history is the implementation archive; compatibility with historical local data is implemented inside the canonical `testamur` package.

The current direction is:

```text
historical witness_* SQLite / wtn:* / old serialized records
        ↓ explicit compatibility reader / migration logic in testamur
canonical Testamur runtime/model
        ↓
new writes use Testamur identity
```

There is no supported reverse or shim runtime:

```text
testamur -> witness                # forbidden
new caller -> witness shim         # retired
witness package as compatibility   # retired
```

## What may remain historical

Persisted identifiers are not live namespaces. The following may remain when changing them would break durable data or content-address identity:

- `witness_*` SQLite table names;
- historical `wtn:*` references already stored in local data;
- historical wire/version tokens required to reconstruct old records;
- hash-participating CAS/snapshot version tokens;
- already-created legacy random IDs.

These are read/migration/serialization inputs only. They do not authorize new Witness-named writes or public Python types.

Do not rename physical schema identifiers by string replacement. A physical migration requires a transactional, versioned migration plus reopen/round-trip tests.

## New-write rules

New product/runtime writes must be Testamur-owned.

Current release invariants include:

- new runtime envelopes use the canonical Testamur protocol token;
- new runtime run/event references use the `tst:*` family;
- new command-execution records use Testamur identity;
- new graph-store project/object/revision/edge/verification identifiers use Testamur prefixes;
- public runtime/revision/versioned store classes are Testamur-owned;
- active validation/error wording does not present Witness as the current product.

A historical object may remain readable without becoming canonical for new writes.

## Executable namespace inventory

Do not maintain a manual list of reverse imports. The executable scanners remain authoritative for static and literal dynamic imports:

```python
from testamur.convergence import legacy_import_report
report = legacy_import_report(repo_root)
```

Canonical-package reverse imports are release-blocking. Testamur tests importing the retired runtime are also release-blocking through `audit_release_surface()`.

The structural release audit must reject:

- active `witness/` or `witness_service/` runtime trees;
- shipped Witness package patterns or CLI entrypoints;
- production `testamur -> witness` imports;
- `tests/test_testamur_* -> witness` imports;
- canonical `mathhub.py -> witness` imports.

## Historical runtime compatibility

Legacy runtime records are reconstructed from their persisted identity. Historical `wtn:*` runs remain readable, but the canonical runtime must not append new events to them. A caller that wants to continue recording work starts a new Testamur runtime run.

This gives a clean boundary:

```text
old run: readable / immutable compatibility history
new run: Testamur protocol + Testamur identity
```

Compatibility must preserve semantic invariants:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
lineage != affectedness verdict
```

Reopening old bytes must never promote them into a stronger epistemic state.

## MathHub boundary

MathHub remains a separate mathematical product. Removing Witness must not make canonical `mathhub.py` depend on a retired package, and Testamur must not depend on MathHub as a hidden semantic engine.

The shared transition repository may contain both products while the split is prepared, but namespace compatibility is owned by Testamur and mathematical proof semantics remain owned by MathHub.

## Release validation

For an exact checkout:

```bash
bash scripts/testamur_local_gate.sh release
```

Release mode:

1. compiles the shipped `testamur` package and canonical `mathhub.py`;
2. runs the structural release-surface audit;
3. verifies required W1-W5 semantic release tests still exist;
4. runs the complete current `tests/test_testamur_*.py` regression suite;
5. includes fresh-install coverage proving the distributed Testamur package does not contain Witness runtime packages.

GitHub Actions may invoke the same local gate, but Actions availability is not part of the semantic contract. An unexecuted job is not green and an unavailable runner is not itself a product failure.

## Completion condition

Namespace retirement is considered structurally complete when the exact candidate head satisfies the executable release audit and historical compatibility tests while all new writes/public types remain Testamur-owned.

Repository extraction/publication and open-source license selection are separate completion steps described by `docs/TESTAMUR_COMPLETION_SPEC.md`.
