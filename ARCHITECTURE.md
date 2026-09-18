# MathHub Architecture

## 1. Mathematical ontology

MathHub's mathematical layer is deliberately small:

```text
Claim + Proof + ProofDependency
```

### Claim

A Claim is a mathematical proposition. Public Claim registration accepts Lean `theorem` / `lemma` declarations. Definitions, structures, classes, constructors, recursors and instances belong to the formal substrate rather than becoming mathematical Claim nodes.

### Proof

A Proof is one route establishing one Claim revision. Proof source is first-class and multiple Proofs may establish the same Claim.

### ProofDependency

Dependencies belong to Proofs. The public Claim graph is only a projection:

```text
A → B
```

means that at least one active Proof establishing Claim A uses Claim B.

## 2. Formal substrate

Lean is the authority for formal verification.

MathHub records:

- exact `ConstantInfo` / Expr evidence;
- statement references from a declaration type;
- proof references from a theorem/proof value Expr;
- transitive constant closure for audit/provenance;
- exact environment information;
- FormalBindings from Lean declaration names to Claim revisions.

Statement refs do not become mathematical dependencies. Only complete proof-ref audits may generate ProofDependency records.

## 3. Verification and argument witnesses

Verification and argument evidence are conceptually distinct.

For an ordinary local Proof they often originate from the same Build. MathHub still selects them independently:

- verification witness: best Build showing the Proof is complete/kernel-checked;
- argument witness: best Build whose dependency instrumentation completed successfully.

An incomplete newer dependency audit does not erase an older complete argument route.

### Imported existing theorem

An imported library theorem makes this distinction especially explicit.

For external theorem `Nat.add_comm`, MathHub creates a stable local verification bridge:

```lean
theorem MathHub.Import.c... : <elaborated Nat.add_comm type> := by
  exact Nat.add_comm
```

The bridge gives the Claim an ordinary kernel-checked local Proof/Build. The external declaration `Nat.add_comm` is also FormalBound to the same Claim revision.

However, the mathematical argument route must not be reduced to the bridge's trivial `exact Nat.add_comm` reference. For imported mathematics, MathHub re-inspects the **original external theorem ConstantInfo** in the exact pinned environment and appends its original proof Expr constant observations to the imported Proof's ArgumentIndex evidence.

Thus:

```text
verification evidence
  = MathHub local alias bridge

argument evidence
  = original external theorem proof Expr refs
```

The local alias is provenance/verification machinery. The external declaration name is the human-facing formal name and the source of imported mathematical argument structure.

## 4. Automatic theorem dependency closure

Existing Lean mathematics can grow the registry automatically.

For each imported theorem:

```text
original theorem proof Expr
  → direct constant refs
  → resolve existing FormalBindings
  → classify unbound constants with Lean ConstantInfo
      ├─ .thmInfo → theorem Claim candidate
      └─ other ConstantInfo / internal / missing → formal substrate
  → batch-import theorem candidates
  → repeat within explicit budgets
```

The closure is deterministic and non-AI. Names and namespaces are navigation/display aids, not evidence that a constant is a theorem.

Default web bounds:

```text
max_depth = 2
max_claims = 160 per root batch
```

Hard implementation bounds prevent runaway recursive imports. Hitting a boundary returns `truncated=true`; MathHub never calls a bounded result a complete closure.

Raw non-theorem constants remain available for formal inspection but never become ProofDependency Claim edges merely because they were referenced by Lean.

## 5. Batch execution

Mathematical identity remains per theorem, while expensive Lean process startup is shared.

A bounded batch (currently at most 40 theorem roots) performs:

```text
1 Lean process: inspect external declarations
1 Lean process: compile/audit local bridge theorems
N independent Claim / Proof / Build / FormalBinding records
```

A fully duplicate batch is resolved from FormalBinding before Lean invocation and therefore costs zero Lean processes.

Automatic dependency closure composes this batch primitive recursively rather than introducing a second mathematical object type.

## 6. ArgumentIndex

Active dependency truth is stored in ArgumentIndex.

### Immutable raw observations

`build_constant_refs` records:

- statement constants;
- proof constants;
- transitive constants.

### Mathematical projection

`proof_claim_dependencies` maps complete proof observations to exact registered Claim revisions through FormalBinding in the same environment.

Reconciliation is intentionally repeatable: an old immutable Build may gain a new mathematical interpretation when a previously unmapped Lean theorem later receives a FormalBinding. The old Build itself is not recompiled or mutated.

Legacy Claim-like definitions are filtered at reconciliation and never become new mathematical edges.

## 7. Library discovery cache

Large Lean namespaces are expensive to enumerate repeatedly, so MathHub maintains a disposable theorem-name read cache keyed by:

```text
environment_hash + imports fingerprint + namespace
```

The first read enumerates `.thmInfo` constants from the pinned Lean Environment. Later searches use SQLite and launch no Lean process.

The theorem-name index is not source of truth. It can be discarded and rebuilt from Lean at any time.

## 8. Presentation layer

Presentation is separate from mathematical identity and verification.

Canonical rendering priority is:

```text
Lean-pretty current renderer
  > source-declaration current renderer
  > older generated renderer
```

Successful complete audits may provide `ConstantInfo.type → ppExpr` as canonical presentation input. Unbuilt Claims use deterministic source-declaration fallback.

Human curated presentations (`concise`, `textbook`, `intuitive`, `translation`) are append-only display records and do not alter Claim/Proof/dependency truth.

Current deterministic surface representation is `surface-ir-v3`.

## 9. Global graph read model

The web graph is persistent rather than replace-on-recenter.

Literal all-Claim detail is used only while both readability budgets hold:

```text
Claims ≤ 300
projected edges ≤ 1500
```

Larger registries use hierarchical LOD:

```text
curated area
  > imported external Lean namespace
  > local Claim Lean namespace
```

Namespace clusters drill down recursively, and direct Claims are cursor-paged. Nodes persist on Canvas while a cluster's aggregate projection edges are replaced by progressively refined edges.

This lets mathlib-scale registries preserve an Obsidian-like global-world feeling without downloading or drawing every theorem simultaneously.

## 10. Provenance

Claim revisions, Proofs, Builds, FormalBindings, raw constant observations and presentations are append-only or immutable where they represent evidence.

Public object IDs are opaque stable identifiers. SQLite integer primary keys remain internal implementation details.

MathHub's trust chain remains:

```text
Claim
← Proof
← Lean kernel verification
← exact environment
← proof-specific argument evidence
```

Presentation, graph layout, clustering and derived caches may improve navigation, but none of them become mathematical authority.

## 11. Testamur / MathHub boundary

MathHub remains a distinct mathematical product and ontology inside the current transition repository. Testamur provides generic provenance, source/revision, reliance, temporal, lineage and revalidation infrastructure; it is **not** a replacement for MathHub's mathematical model.

In particular:

- `Claim`, `Proof`, and `ProofDependency` remain MathHub-owned mathematical concepts;
- `Proof` is not renamed to generic evidence;
- `ProofDependency` remains proof-specific mathematical dependency evidence;
- Lean remains the authority for formal verification;
- Testamur verification/reliance state does not replace MathHub's exact Build/kernel state;
- MathHub may consume or project into shared Testamur provenance infrastructure only through explicit boundaries;
- Testamur core must not depend on MathHub as a hidden semantic engine.

The intended ownership relationship is:

```text
Testamur core / provenance infrastructure
            ↑ explicit adapter/projection
        MathHub domain model
            ↓
Lean environment + kernel
```

The repository is transitional. The target split keeps public Testamur core/integrations and the MathHub product independently understandable, while any hosted account/billing/service-plane code lives outside the OSS semantic core.

See `README.md`, `docs/MATHHUB_PRODUCT.md`, and `docs/TESTAMUR_COMPLETION_SPEC.md` for the current product/repository boundary.
