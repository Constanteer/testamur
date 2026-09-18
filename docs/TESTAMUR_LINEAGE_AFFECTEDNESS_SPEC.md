# Testamur Lineage & Affectedness Spec

> **Status:** canonical lineage/affectedness semantics specification for the converged Testamur core.
>
> This spec defines how Testamur represents derivation, forks, embedded upstream material, transformations, advisories, and the question “does an upstream change actually affect this downstream object?”. The landed implementation contract is `TESTAMUR_LINEAGE_ENGINE.md`; Policy/Reliance ownership is defined by `TESTAMUR_CONVERGENCE.md`. Historical Witness design documents are archival context rather than active owners.

## 1. Purpose

A dependency graph is not enough.

If object `B` came from object `A`, and `A` later receives a vulnerability advisory, retraction, correction, or other adverse event, Testamur must **not** blindly copy that status onto `B`.

The system must preserve enough lineage to ask:

> What material from the affected upstream revision survives in this downstream revision, under what transformations, and what evidence establishes whether the adverse condition is still applicable?

This is the difference between **propagating attention** and **propagating a conclusion**.

The generic flow is:

```text
upstream revision/event
      ↓
lineage candidates
      ↓
potentially affected downstream revisions
      ↓
applicability analysis
      ↓
evidence-backed affectedness assessment
      ↓
reliance / policy propagation
```

---

## 2. Core invariants

1. **Lineage is revision-pinned.** A relation between mutable project names is insufficient when exact revisions are available.
2. **Derivation is not equivalence.** A fork, copy, vendor operation, translation, build, summary, or model transformation may preserve some upstream properties and destroy others.
3. **An upstream advisory creates attention, not automatic guilt.** Transitive lineage may justify `POTENTIALLY_AFFECTED`; stronger states require evidence.
4. **Absence of a known advisory is not evidence of safety.**
5. **A patch claim is not a mitigation fact until its scope is established.**
6. **Historical affectedness is immutable.** Later analysis may supersede an earlier assessment but must not rewrite it.
7. **Affectedness is purpose- and condition-scoped.** One downstream artifact may be affected for one capability or deployment configuration and unaffected for another.
8. **Unknown is valid.** If applicability cannot be established, the result remains unknown or potentially affected.

---

## 3. Lineage relation vocabulary

The portable core should support semantics equivalent to the following relation families. Concrete schema names may differ, but their meanings must remain distinct.

### 3.1 `DERIVED_FROM`

The downstream object was materially produced from the upstream object.

Examples:

```text
fork commit        DERIVED_FROM upstream commit
translated dataset DERIVED_FROM source dataset
summary            DERIVED_FROM document revision
compiled binary    DERIVED_FROM source tree revision
```

This relation does **not** claim that all upstream properties survive derivation.

### 3.2 `CONTAINS`

The downstream object contains an identifiable upstream object or portion.

Examples:

```text
monorepo revision CONTAINS vendored library revision
container image   CONTAINS package artifact
paper bundle      CONTAINS dataset snapshot
```

Where possible, a containment relation should record a location, component identity, range, manifest entry, or other deterministic witness.

### 3.3 `PATCHED_FROM`

The downstream revision was created by applying one or more patches to a known upstream revision.

Recommended metadata:

```text
base_revision
patch_artifacts[]
patch_order
result_digest
build_or_apply_receipt
```

`PATCHED_FROM` does not imply that a particular defect was fixed.

### 3.4 `TRANSFORMS`

A deterministic or declared transformation maps an upstream object into a downstream object.

Recommended metadata:

```text
transform_id
transform_version
parameters_digest
input_revision
output_revision
receipt
```

Examples include normalization, compilation, extraction, conversion, filtering, anonymization, and deterministic code generation.

### 3.5 `SUPERSEDES`

A revision or artifact is intended to replace another for a declared scope.

`SUPERSEDES` is an authority or lifecycle relation, not semantic equivalence.

### 3.6 `EQUIVALENT_TO`

Two revisions are established as equivalent under an explicit equivalence scope and verifier.

Examples:

```text
byte-equivalent
normalized-text-equivalent
ABI-equivalent for declared interface
proof-term-equivalent under environment E
```

The relation must identify:

```text
equivalence_scope
verifier / authority
receipt
policy context if applicable
```

Testamur must never infer universal equivalence from matching names, version strings, similar text, or an AI judgment alone.

---

## 4. Lineage evidence boundary

Lineage facts must retain the same observed / derived / declared discipline used elsewhere in Witness.

### OBSERVED

Examples:

```text
Git parent commit
archive digest
lockfile entry
SBOM component digest
binary section digest
patch bytes
build input manifest
```

### DERIVED

Examples:

```text
file survived fork unchanged
function body matches upstream range
binary embeds component digest
patch touches vulnerable source range
symbol mapping between source and binary
```

Derived lineage facts must name the deterministic analyzer and version.

### DECLARED

Examples:

```text
"this fork removed the vulnerable subsystem"
"this patch mitigates CVE-X"
"these two implementations are semantically equivalent"
```

Declarations may come from maintainers, agents, auditors, vendors, or other authorities, but declarations remain declarations unless backed by stronger evidence.

---

## 5. Adverse events

Affectedness analysis starts from an event attached to an exact object/revision/range or to a resolvable upstream identity.

Generic event classes include:

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

An event should carry, where applicable:

```text
event_id
event_class
issuer / source
issued_at
upstream_identity
known_affected_revision_range
known_unaffected_revision_range
condition / configuration
affected_component_or_region
severity or external metadata
source_revision / advisory snapshot
```

External labels such as CVE or KEV are source facts. Testamur's own affectedness assessment is a separate object.

---

## 6. Affectedness state machine

The generic affectedness states are:

```text
POTENTIALLY_AFFECTED
CONFIRMED_AFFECTED
MITIGATED
DISPROVEN
UNKNOWN
NOT_APPLICABLE
```

These states describe applicability of a particular event to a particular downstream revision. They are not global trust states for the artifact.

### 6.1 `POTENTIALLY_AFFECTED`

Lineage or dependency evidence establishes a plausible path from the affected upstream material to the downstream revision, but applicability has not been resolved.

This should be the normal first state for transitive propagation.

### 6.2 `CONFIRMED_AFFECTED`

Evidence establishes that the condition described by the event survives in the downstream revision under the declared scope/configuration.

Examples:

- exact vulnerable code range is present and reachable under the advisory's conditions;
- vulnerable package revision is present in the shipped artifact;
- corrected dataset rows are exactly those used by the downstream analysis.

### 6.3 `MITIGATED`

The affected material or condition exists in lineage, but an explicit mitigation prevents the adverse condition under the declared scope.

Mitigation must identify its evidence and scope. It must not be interpreted as removal of lineage.

### 6.4 `DISPROVEN`

Evidence establishes that the event does not apply to this downstream revision despite a plausible lineage path.

Examples:

- vulnerable code was removed before the downstream revision;
- the relevant function was replaced with independently implemented code;
- the affected feature is absent from the built artifact and this absence is mechanically established;
- the advisory only applies to a configuration that the artifact provably cannot instantiate.

### 6.5 `NOT_APPLICABLE`

The event definition itself excludes the downstream revision or deployment scope without requiring a mitigation claim.

### 6.6 `UNKNOWN`

The system cannot currently establish either applicability or non-applicability.

`UNKNOWN` must not be silently converted to `DISPROVEN` because a scanner failed to find a match.

---

## 7. Propagation algorithm

Given adverse event `E` on upstream revision or component `U` and candidate downstream revision `D`:

```text
1. Resolve E to exact known affected upstream identity/range where possible.
2. Find lineage paths U → ... → D.
3. Reject paths that are provably irrelevant to the event scope.
4. Collect survival evidence across each transformation/containment step.
5. If a plausible path remains, create POTENTIALLY_AFFECTED.
6. Run available deterministic applicability analyzers.
7. Incorporate signed/declared mitigation or maintainer evidence without upgrading it beyond its evidence class.
8. Produce a scoped assessment:
      CONFIRMED_AFFECTED / MITIGATED / DISPROVEN / NOT_APPLICABLE / UNKNOWN.
9. Record the exact graph snapshot, analyzer versions, evidence, policy, and time.
10. Propagate attention to actual downstream RELIANCE edges according to policy.
```

Important distinction:

```text
lineage propagation      → candidate affectedness
applicability assessment → event-specific conclusion
reliance propagation     → operational blast radius
```

These are three different operations and must not be collapsed.

---

## 8. Fork semantics

A fork retains ancestry even after substantial divergence.

Therefore this is invalid:

```text
fork has many changed lines
→ assume upstream advisory no longer matters
```

And this is also invalid:

```text
fork descends from affected version
→ mark fork CONFIRMED_AFFECTED forever
```

Instead Testamur asks whether the **event-relevant material** survived.

For a software fork, useful evidence may include:

```text
merge-base / ancestry
file identity
patch-id
AST / symbol mapping
function- or region-level hashes
build manifests
SBOM evidence
binary symbol / section evidence
feature configuration
reachable call graph
maintainer patch declarations
regression / exploit-specific verifier receipts
```

A fork can therefore remain deeply derived from upstream while being `DISPROVEN` or `MITIGATED` for one advisory and `CONFIRMED_AFFECTED` for another.

---

## 9. CVE / KEV semantics

CVE and KEV records are especially important examples because package-name and version-range matching is often insufficient for forks, vendored code, backports, distro patches, and custom builds.

### 9.1 Ingestion

An advisory source should be captured as a versioned source revision using the source supply-chain rules.

The system stores external facts separately from local conclusions:

```text
external advisory says:
  upstream package P versions X..Y affected

Testamur lineage says:
  downstream fork F derived from P@X
  vulnerable region may / may not survive

Testamur assessment says:
  F@R = POTENTIALLY_AFFECTED / CONFIRMED_AFFECTED / MITIGATED / DISPROVEN / UNKNOWN
```

### 9.2 KEV propagation

Presence in a known-exploited catalog may raise operational urgency, but it does not alter lineage semantics.

A KEV event may change policy behavior such as:

```text
POTENTIALLY_AFFECTED + KEV
→ block release until resolved
```

while another project policy may allow a temporary documented exception.

The catalog does not become a universal Testamur truth score.

### 9.3 Backports

A backported security fix should be represented as lineage plus mitigation evidence rather than by falsifying the package version.

Example:

```text
DistroPackage 1.4-r7
  PATCHED_FROM Upstream 1.4
  CONTAINS Patch P17

Assessment for CVE-X:
  MITIGATED
  because P17 is established to remove/neutralize the affected condition
```

This preserves both ancestry and the reason the normal upstream version-range rule is insufficient.

### 9.4 Vendored and copied code

If vulnerable code was copied rather than installed as a named dependency, exact package inventory may miss it.

Testamur should allow lineage discovery from content/structure evidence to create a candidate relation:

```text
VendoredRegion V
  DERIVED_FROM UpstreamRegion U
```

That relation remains provenance-bearing and confidence/scoping information must be preserved if it is derived rather than observed.

---

## 10. Non-software affectedness

The same machinery applies outside cybersecurity.

### 10.1 Dataset correction

```text
Dataset R1
  ↓ transformed by filter F
Derived Dataset D
  ↓ used by
Analysis A
```

If R1 receives a correction, Testamur asks whether corrected records survived `F` into `D` and whether `A` actually relied on them.

### 10.2 Retraction / paper correction

A retracted paper does not make every work that cited it false.

The system should identify which downstream claims actually relied on the retracted result and whether alternative support exists.

### 10.3 Formal environments

A theorem checker or library correction may stale proofs built under an older environment without asserting the mathematical statement is false.

### 10.4 Instrument calibration

A calibration invalidation may affect only measurements produced in a time/range/configuration window. Lineage and actual reliance determine blast radius.

---

## 11. Relationship to reliance and policy

Affectedness and reliance are separate.

An artifact can be `CONFIRMED_AFFECTED` by an advisory yet have no effect on a particular project because that project never relied on the affected artifact/revision.

Conversely, unresolved `POTENTIALLY_AFFECTED` state may be enough for a strict policy to suspend current reliance.

Example:

```text
Event E
  ↓ applies-to?
Artifact F@R
  ↓ RELIED_ON_BY
Release X

Policy:
  if KEV and affectedness in {POTENTIALLY_AFFECTED, CONFIRMED_AFFECTED, UNKNOWN}
  then Release X = REVIEW_REQUIRED / BLOCKED
```

A different policy can produce a different action without changing the underlying evidence graph.

---

## 12. Historical semantics

Each affectedness assessment must pin:

```text
subject revision
event revision / source snapshot
lineage graph snapshot or sufficient referenced revisions
analyzer versions
evidence refs
policy ref if action was derived
assessment state
created_at
supersedes assessment id if applicable
```

When new evidence arrives, create a new assessment.

Example:

```text
2026-09-16  POTENTIALLY_AFFECTED
2026-09-17  DISPROVEN   supersedes prior assessment
```

Historical queries for September 16 must still show that the state was unresolved at that time.

---

## 13. APIs / engine responsibilities

A future implementation should expose boundaries equivalent to:

```python
record_lineage(subject_revision, relation, upstream_revision, *, evidence, scope=None)
lineage_paths(upstream_revision, downstream_revision=None, *, relation_filter=None)
record_adverse_event(event)
find_potentially_affected(event_id, *, scope=None)
assess_affectedness(event_id, subject_revision, *, policy=None)
get_affectedness(event_id, subject_revision, *, as_of=None)
explain_affectedness(assessment_id)
affected_reliance_blast_radius(event_id, *, policy=None, as_of=None)
```

`explain_affectedness` must return evidence and reasoning structure, not only a label.

---

## 14. Fail-closed requirements

The system must not:

- mark all descendants of an affected upstream revision `CONFIRMED_AFFECTED` merely because ancestry exists;
- mark a divergent fork safe merely because its version/name differs;
- treat a maintainer's “fixed” statement as observed mechanical proof;
- erase ancestry after a patch is applied;
- infer semantic equivalence from identical version strings or names;
- treat scanner non-detection as proof of absence;
- silently move historical assessments to the newest advisory revision;
- conflate `MITIGATED`, `DISPROVEN`, and `NOT_APPLICABLE`;
- conflate vulnerability affectedness with overall artifact trustworthiness;
- propagate an event to downstream project state without distinguishing lineage from actual reliance.

---

## 15. Minimum viable implementation

MVP should support one concrete software path end-to-end:

```text
Git repository / package revision
→ exact ancestry + containment lineage
→ ingest advisory snapshot
→ resolve upstream affected revision/range
→ find downstream fork/vendor candidates
→ POTENTIALLY_AFFECTED
→ deterministic region/file/patch comparison where possible
→ explicit affectedness assessment
→ RELIANCE blast radius
→ policy decision
→ historical explanation
```

The first implementation does not need perfect semantic code equivalence. It needs to preserve uncertainty and make each upgrade from “possible” to “resolved” inspectable.

Suggested implementation order:

```text
1. exact Git ancestry / package revision lineage
2. vendored component + manifest containment
3. advisory ingestion + revision pinning
4. potentially-affected propagation
5. patch / file / region evidence
6. affectedness assessment objects
7. reliance-aware blast radius
8. policy gates
9. agent-facing explain endpoint
10. richer code/binary matching analyzers
```

---

## 16. Product principle

The important question is not:

> Does this fork descend from something vulnerable?

Nor is it:

> Did a scanner find the old package name?

It is:

> **Which event-relevant upstream material survived into the exact object we rely on, what evidence establishes its applicability now, and what downstream reliance actually changes because of it?**

Testamur should propagate reasons and uncertainty before it propagates verdicts.
