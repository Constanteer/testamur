# Testamur Lineage Engine

> **Status:** canonical landed lineage/affectedness implementation contract on the Testamur convergence line.
>
> Historical W5 worker branches are no longer semantic owners; current ownership is defined by `TESTAMUR_CONVERGENCE.md` and the #171/#172 convergence stack.

This document describes the canonical Testamur implementation of transformed-artifact lineage and adverse-event affectedness. It implements the distinctions in `TESTAMUR_LINEAGE_AFFECTEDNESS_SPEC.md` without extending the legacy Witness runtime or overloading the small generic `Record/Relation` vocabulary.

## 1. Semantic split

The engine deliberately has three separate layers:

```text
external advisory / adverse-event fact
        ↓
revision-pinned typed lineage candidate propagation
        ↓
evidence-backed affectedness assessment
        ↓
optional W3 reliance / policy propagation
```

These operations are not interchangeable.

```text
lineage propagation != vulnerability verdict
POTENTIALLY_AFFECTED != CONFIRMED_AFFECTED
changed derivative != safe
name/version match alone != affected
scanner non-detection != disproven
no known vulnerability != secure
DECLARED != mechanically established
```

`UNKNOWN` is a first-class result.

## 2. Modules

### `testamur/component_identity.py`

Provides strict stable component identity and revision identity:

- `ComponentIdentity`
- `ComponentRevisionIdentity`
- `same_component`

Component equality is intentionally strict. Similar names, aliases and equal version strings do not imply equivalence. Revision identity records whether its strongest discriminator is content-addressed, revision-pinned, version-only or locator-only.

### `testamur/lineage.py`

Provides the append-only typed lineage graph:

```text
DERIVED_FROM
CONTAINS
PATCHED_FROM
TRANSFORMS
SUPERSEDES
EQUIVALENT_TO
```

Every lineage edge requires explicit evidence classified as:

```text
OBSERVED
DERIVED
DECLARED
```

Derived evidence must identify analyzer and analyzer version. `EQUIVALENT_TO` additionally requires an explicit equivalence scope.

The stored edge direction is:

```text
upstream_ref -> downstream_ref
```

The public recording API follows the product wording:

```python
record_lineage(
    subject_revision,       # downstream
    relation,
    upstream_revision,
    *,
    evidence,
    scope=None,
    component_mapping=None,
    metadata=None,
)
```

Traversal is deterministic, cycle-safe and hard-bounded by both depth/path limits and an internal expansion budget. An explicitly empty relation filter yields no traversal rather than silently widening to all relations. By default affectedness-oriented traversal follows material-continuity relations and excludes `SUPERSEDES`; lifecycle replacement alone is not proof that upstream material survived.

Scoped `EQUIVALENT_TO` is traversable from either endpoint. Reverse traversal retains the same immutable evidence-bearing edge and is marked `traversal_reversed=true`; symmetry never widens the recorded equivalence scope and still implies no affectedness verdict.

### `testamur/lineage_projection.py`

Provides one-way compatibility projection helpers without importing `witness.*` at runtime.

`lineage_evidence_from_legacy_source_anchor(...)` preserves exact legacy `source_revision_id`, evidence ID, anchor digest and representation identity. A legacy `DERIVED` anchor must expose the versioned extractor identity that produced it; missing extractor provenance fails closed.

`project_legacy_fork_result(...)` converts a legacy fork's `object_id_map` into `DERIVED_FROM` edges only when the caller supplies exact source and target revision bindings. Legacy object IDs are not treated as revision identity. Missing bindings are returned under `unresolved` and produce no edge. The projection explicitly records that verification authority is not inherited.

This is intentionally projection, not a second source-supply-chain implementation. W1 owns canonical convergence of the mature source/revision substrate.

### `testamur/vendor_lineage.py`

Projects exact vendored/embedded component evidence into canonical `CONTAINS` lineage. The helper requires an exact component revision, canonical component identity, a concrete downstream location, and versioned derived-analyzer evidence. Package name/version metadata alone is not promoted into lineage or affectedness.

### `testamur/advisory.py`

Provides an append-only provider-neutral adverse-event store. Stable event identity is separated from immutable advisory revisions.

Supported generic event classes include:

```text
VULNERABILITY_ADVISORY
KNOWN_EXPLOITED_VULNERABILITY
RETRACTION
DATA_CORRECTION
CALIBRATION_INVALIDATION
LICENSE_OR_POLICY_CHANGE
COMPROMISED_RELEASE
WITHDRAWAL
ERRATUM
FAILED_REPRODUCTION
```

External provider labels and version/range statements are source facts. They do not become Testamur affectedness conclusions automatically.

### `testamur/advisory_adapters.py`

Defines a small provider adapter boundary and an initial `OSVAdvisoryAdapter`.

The OSV adapter preserves:

- OSV ID / aliases;
- affected package identity;
- provider-declared versions and ranges;
- source revision reference;
- published/modified metadata;
- provider severity values.

It intentionally does **not** decide whether a fork, vendored copy, distro backport or custom build is affected. If an advisory only supplies package/range identity and no exact Testamur upstream revision binding exists, candidate propagation stays fail-closed until a separate evidence-bearing identity-to-revision resolver is available.

### `testamur/affectedness.py`

Provides immutable historical affectedness assessments and the candidate/application engine.

States:

```text
POTENTIALLY_AFFECTED
CONFIRMED_AFFECTED
MITIGATED
DISPROVEN
NOT_APPLICABLE
UNKNOWN
```

Applicability evidence uses explicit signals:

```text
MATERIAL_PRESENT
MATERIAL_ABSENT
MITIGATION_ESTABLISHED
MITIGATION_DECLARED
OUT_OF_SCOPE
INCONCLUSIVE
SCANNER_NO_MATCH
```

Automatic resolution is deliberately conservative:

- `SCANNER_NO_MATCH` only contributes to `UNKNOWN`; it never upgrades to `DISPROVEN`;
- `MITIGATION_DECLARED` does not auto-resolve to `MITIGATED`;
- evidence whose provenance class is only `DECLARED` remains `UNKNOWN` without observed/derived corroboration;
- conflicting presence/absence or scope evidence resolves to `UNKNOWN` rather than fabricating certainty.

This does not forbid a purpose-specific W3 policy from accepting a declaration. It only prevents the W5 mechanical resolver from silently treating authority/attestation as observation.

Final resolved states require explicit applicability evidence. `POTENTIALLY_AFFECTED` requires concrete lineage support.

A candidate may have more than one valid ancestry path. The immutable assessment stores the complete recorded lineage-edge basis rather than pretending multiple paths are one ordered chain. `affectedness_explain.py` reconstructs the actual path alternatives from those exact recorded endpoints.

New evidence creates a new assessment and may reference `supersedes_assessment_id`; previous assessments remain immutable. A newer advisory revision may supersede an older assessment for the same derivative subject while preserving both event revisions in history.

### `testamur/affectedness_explain.py`

Hydrates an assessment into an explainable advisory-to-derivative path using only lineage edges already pinned by that assessment. It:

- retrieves the immutable advisory revision when available;
- hydrates every pinned lineage edge;
- reconstructs simple directed paths to the assessed subject;
- preserves alternate paths rather than collapsing them;
- reports missing edge/advisory references explicitly;
- never guesses a missing edge or treats the path itself as an affectedness verdict.

### `testamur/affectedness_reliance.py`

Bridges exact W5 affected revision references to W3 durable reliance receipts.

W3 receipts pin:

```text
object_ref -> exact revision_ref
```

W5 affectedness subjects are exact revision refs. Therefore an affected revision must be matched against the **values** of `pinned_revisions`. Passing a W5 revision ref directly to an object-keyed `blast_radius(changed_object_refs=...)` would be semantically wrong and can miss real reliance.

`RevisionPinnedRelianceResolver` uses W3's public receipt listing surface and performs exact pinned-revision matching. It returns only actual durable reliance receipts/reliants. An optional policy filter matches the receipt's pinned policy IDs.

## 3. Canonical software flow

```text
U@A
  ↓ DERIVED_FROM
F@B
  ↓ TRANSFORMS / CONTAINS
V@C

Advisory revision E says upstream U@A / upstream identity is affected.

find_potentially_affected(E)
  -> F@B POTENTIALLY_AFFECTED
  -> V@C POTENTIALLY_AFFECTED

region/patch/build evidence then resolves each subject independently:
  MATERIAL_PRESENT        -> CONFIRMED_AFFECTED
  MITIGATION_ESTABLISHED  -> MITIGATED
  MATERIAL_ABSENT         -> DISPROVEN
  OUT_OF_SCOPE            -> NOT_APPLICABLE
  insufficient/conflicting/scanner-only/declaration-only evidence -> UNKNOWN

exact affected revision
  -> match W3 receipt.pinned_revisions values
  -> only actual durable reliance becomes downstream review/blast radius
```

A backported package therefore keeps `PATCHED_FROM` ancestry while an advisory-specific assessment can be `MITIGATED`. The version string does not need to be falsified to pretend it is a pristine upstream fixed release.

The vendoring E2E exercises the same boundary with a canonical component revision: exact `CONTAINS` evidence creates only `POTENTIALLY_AFFECTED`; region-presence evidence can later resolve `CONFIRMED_AFFECTED`, while region-absence evidence can resolve `DISPROVEN` without deleting containment ancestry.

## 4. Historical behavior

Affectedness is append-only:

```text
T1  POTENTIALLY_AFFECTED
T2  DISPROVEN supersedes T1
```

T1 remains queryable. The implementation currently exposes revision-specific history; W2 may later supply explicit `KNOWN_AT` / `AVAILABLE_BY` projection without rewriting W5 rows.

## 5. W3 integration hook

W5 does not import a concrete W3 reliance module. `testamur.affectedness.RelianceImpactResolver` defines the narrow hook:

```python
blast_radius_for_refs(refs: Sequence[str], *, policy_ref: str | None = None)
```

`TestamurAffectednessEngine.affected_reliance_blast_radius(...)` sends only subjects whose latest assessment is in the selected actionable state set. Default actionable states are:

```text
POTENTIALLY_AFFECTED
CONFIRMED_AFFECTED
UNKNOWN
```

`MITIGATED`, `DISPROVEN`, and `NOT_APPLICABLE` are excluded from the default operational blast-radius request, but callers may explicitly choose another state set under policy.

`RevisionPinnedRelianceResolver` already satisfies this hook against the current W3 receipt-listing contract by exact `pinned_revisions` value matching, so W5 does not require W3 to add a parallel truth model or change receipt identity.

### INTEGRATION REQUEST — W3

Keep the receipt-listing contract stable enough to expose `pinned_revisions`, `policy_ids`, `reliant_ref`, `reliant_revision_ref`, purpose and current stale/admissibility metadata. A future native `blast_radius_for_revision_refs(...)` would be a convenience/performance improvement, not a semantic requirement.

W3 should own the authority decision for declaration-only evidence. W5 preserves the declaration and leaves automatic mechanical resolution at `UNKNOWN`.

## 6. W1 integration requests

### INTEGRATION REQUEST — W1 / canonical hashing

W5 currently uses `testamur.component_identity.canonical_json/canonical_hash` to avoid creating any new `witness.*` runtime dependency. Once W1's canonical `testamur.runtime_protocol` / shared serialization helper is merged, W1 may replace these helpers with the canonical shared implementation if the byte-for-byte canonical form is identical. Do not change already persisted W5 IDs silently.

### INTEGRATION REQUEST — W1 / source-revision projection

Preserve the mature source-supply-chain semantics during canonical migration: mutable locator != exact source revision, exact source/retrieval digest is durable identity evidence, and source EvidenceAnchor/Region objects remain pinned to the exact source revision. W5's compatibility projector consumes plain mappings so W1 can expose the canonical equivalent without W5 importing legacy modules.

### INTEGRATION REQUEST — W1 / advisory subject binding

Provide or expose an evidence-bearing resolver from provider package/component identity and range evidence to exact canonical Testamur component/source/object revision references. It must not treat package name/version equality alone as affectedness. Until such a resolver exists, OSV-style provider identity without exact upstream refs remains non-propagating rather than guessed.

### INTEGRATION REQUEST — W1 / object projection

Expose the following W5 families through the canonical product/read API without forcing them into the legacy five-string relation vocabulary:

```text
component / component revision identity
lineage edge
advisory / adverse-event revision
affectedness assessment
```

If W1 establishes a generic durable extension envelope, project W5 objects into it while preserving W5 IDs and append-only history.

### INTEGRATION REQUEST — W1 / CLI

Final CLI/product wiring should support the semantic sequence rather than a one-shot vulnerability label:

```text
record/inspect lineage
record/import advisory
show potential candidates
attach applicability evidence
record resolved/unknown assessment
explain assessment
ask reliance blast radius
```

For vendored software, wire exact SBOM/manifest component revision -> `record_vendored_component()` -> advisory revision -> potential candidate -> applicability evidence -> assessment -> W3 exact-revision reliance impact. Do not replace that chain with package-name/version matching.

## 7. Tests added by W5

- `tests/test_testamur_lineage_engine.py`
  - strict component identity;
  - typed/evidence-bearing lineage;
  - scoped equivalence and symmetric traversal within its recorded scope;
  - idempotent lineage writes;
  - deterministic bounded traversal;
  - `SUPERSEDES` excluded from affectedness traversal by default.

- `tests/test_testamur_lineage_bounds.py`
  - empty relation filter is fail-closed;
  - path count is hard bounded on a high-branching graph.

- `tests/test_testamur_lineage_projection.py`
  - exact legacy source evidence identity preserved;
  - derived legacy anchors require versioned extractor provenance;
  - legacy fork projection requires exact source/target revision bindings;
  - unresolved fork objects do not receive fabricated lineage.

- `tests/test_testamur_vendor_lineage.py`
  - exact `CONTAINS` projection;
  - canonical component identity and concrete location preserved;
  - missing revision/location fails closed;
  - name/version metadata does not become an affectedness verdict.

- `tests/test_testamur_vendor_advisory_e2e.py`
  - exact vendored component -> advisory -> `POTENTIALLY_AFFECTED`;
  - explicit region-presence evidence -> `CONFIRMED_AFFECTED` with candidate history preserved;
  - region-absence evidence -> `DISPROVEN` without erasing `CONTAINS` lineage.

- `tests/test_testamur_affectedness_engine.py`
  - fork/vendor candidate propagation;
  - `POTENTIALLY_AFFECTED -> CONFIRMED_AFFECTED`;
  - backport mitigation;
  - removed vulnerable region -> `DISPROVEN`;
  - scanner non-detection -> `UNKNOWN`;
  - conflicting evidence -> `UNKNOWN`;
  - generic reliance-blast-radius hook.

- `tests/test_testamur_affectedness_regressions.py`
  - declaration-only mitigation remains `UNKNOWN` under the mechanical resolver;
  - explicit mitigation declarations do not auto-promote;
  - newer advisory revisions can supersede older assessments for the same subject.

- `tests/test_testamur_affectedness_explain.py`
  - advisory + recorded lineage edge hydration;
  - ordered ancestry reconstruction from immutable edge endpoints;
  - missing references remain explicit rather than guessed.

- `tests/test_testamur_affectedness_reliance.py`
  - W5 revision refs match W3 `pinned_revisions` values, not object keys;
  - policy filtering;
  - object ref is not mistaken for revision ref.

- `tests/test_testamur_affectedness_reliance_e2e.py`
  - advisory -> lineage -> confirmed derivative -> exact pinned downstream reliance;
  - unrelated receipts excluded;
  - `DISPROVEN` latest assessment removes the default operational blast radius.

- `tests/test_testamur_advisory_adapter.py`
  - OSV normalization;
  - provider range/version evidence preserved without verdict promotion.

## 8. Deliberate non-goals in this layer

W5 does not:

- infer semantic equivalence from AI similarity;
- implement a universal vulnerability scanner;
- parse every ecosystem's version-range semantics into local truth;
- create a global trust or risk score;
- mark every descendant of an advisory subject `CONFIRMED_AFFECTED`;
- mark a divergent fork safe because its package name/version changed;
- treat a maintainer declaration as mechanical observation;
- duplicate W1's canonical source/revision substrate;
- own W3 policy/reliance semantics;
- own W2 temporal query semantics;
- edit shared CLI/package entrypoints reserved for W1.
