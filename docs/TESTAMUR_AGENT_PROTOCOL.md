# Testamur Agent / WorkSession Protocol

> **Status:** W4 canonical local protocol and persistence contract.
>
> This document defines how passive agent observations close into explicit durable reliance without treating observation, context exposure, citation, or model-visible text as proof of reliance.

## 1. Scope

W4 owns the operational closure:

```text
agent/tool activity
→ WorkSession
→ immutable observations
→ completion
→ reconciliation declarations
→ canonical RelianceSink
→ durable reliance receipt
→ watch candidate
```

W4 does **not** own policy/admission semantics, the canonical reliance object model, Source identity, Watch scheduling, or attestation cryptography. Those are integrated through narrow protocol hooks instead of duplicated here.

## 2. Invariants

The implementation preserves these distinctions:

```text
DISCOVERED != FETCHED / INSPECTED
FETCHED / INSPECTED != EXPOSED_TO_MODEL
EXPOSED_TO_MODEL != model cognition
EXPLICITLY_REFERENCED != relied upon
agent-declared reliance != mechanically proved reasoning
observed-but-unused != active dependency
changed != invalid
stale != false
```

No capture event can directly create `RELIED_ON_BY_PROJECT_OBJECT`. That state is appended only after a `used=yes` reconciliation decision has been successfully exported through the canonical reliance sink.

## 3. WorkSession lifecycle

Canonical operational states are:

```text
OPEN
  ├─> ABORTED
  └─> COMPLETED_UNRECONCILED
          └─> RECONCILED
                  └─> PUSHED
                          └─> ATTESTED
```

Lifecycle rows are append-only. Session metadata is immutable. `ended_at` is the time the session first becomes completed or aborted; later reconciliation/push/attestation does not rewrite it.

A session pins its reconciliation policy at creation:

```text
TRUST_AGENT_DECLARATION
ASK_USER_TO_CONFIRM
MECHANICAL_ONLY
DISABLED
```

`DISABLED` deliberately leaves a completed session unreconciled and therefore archive-only in the W4 core. A product surface that wants publication of unreconciled sessions must expose that distinction explicitly rather than silently calling the session reconciled.

## 4. Passive source usage

The progression is monotonic in meaning, but not mechanically auto-promoted:

```text
DISCOVERED
FETCHED / INSPECTED
EXPOSED_TO_MODEL
EXPLICITLY_REFERENCED
RELIED_ON_BY_PROJECT_OBJECT
```

`EXPOSED_TO_MODEL` requires a prior `FETCHED` or `INSPECTED` observation for the exact same `SourceRevision`. `EXPLICITLY_REFERENCED` likewise requires observed use of that exact revision.

Exact revision binding is mandatory after discovery. Locator-only candidates may remain archived but cannot be promoted to durable reliance.

Every captured event retains an evidence class and evidence references. Mechanical capture is labeled `MECHANICAL`; reconciliation may use `AGENT_DECLARED` or `HUMAN_CONFIRMED` according to the pinned policy.

## 5. Reconciliation

At completion, `prepare_reconciliation()` returns one input for each `(candidate, exact revision)` observed by the session. A discovered-only candidate is represented as `(candidate, None)` only when no exact revision was ever observed.

A reconciliation declaration is explicit:

```text
candidate_id
source_revision_id
used = yes | no | uncertain
evidence_class
relation_type          # yes only
used_for               # yes only
project_object_ref     # yes only
exact_region_refs      # optional additional evidence
notes
```

The caller must cover every reconciliation input. This prevents silently dropping observed sources at closure. The full declaration set is structurally and policy-validated before any immutable decision row is written, so a bad late declaration cannot strand a partial reconciliation.

A `yes` decision requires:

```text
exact SourceRevision
relation_type
used_for explanation
project object target
non-empty evidence refs
```

`no` and `uncertain` remain provenance only and cannot carry a durable project relation.

### 5.1 Policy evidence classes

```text
TRUST_AGENT_DECLARATION
  accepts AGENT_DECLARED, HUMAN_CONFIRMED, or MECHANICAL

ASK_USER_TO_CONFIRM
  requires HUMAN_CONFIRMED

MECHANICAL_ONLY
  requires MECHANICAL

DISABLED
  performs no reconciliation
```

The evidence class is never relabeled. For example, accepting an agent declaration operationally does not turn it into a mechanically observed fact.

## 6. Durable reliance handoff

W4 exports `used=yes` decisions through `RelianceSink.commit_reliance()` using `RelianceCommitRequest`:

```text
work_session_id
reconciliation_id
decision_id
project_ref
project_object_ref
relation_type
used_for
source_revision_id
evidence_refs
evidence_class
reconciliation_policy
actor_ref
```

The sink returns the canonical `reliance_id`. W4 records that ID as an immutable export receipt; it does not fabricate an independent reliance object. Sink implementations MUST treat `decision_id` as an idempotency key: a remote commit can succeed before a local export receipt is durably recorded, and retry must not create a second semantic reliance. The analogous rule applies to `watch_candidate_id` for `WatchSink`.

A session becomes `RECONCILED` only when every explicit decision is persisted and every `used=yes` decision has a successful durable reliance export. If the sink is unavailable, the decisions remain durable and the session remains `COMPLETED_UNRECONCILED`; calling reconciliation again resumes the missing exports idempotently.

Reconciliation inputs intentionally exclude evidence generated by `RELIED_ON_BY_PROJECT_OBJECT` itself. This prevents the output of reconciliation from feeding back into its own immutable decision identity during retries.

## 7. Watch vs archive lanes

After a successful durable reliance export, W4 creates a deterministic `WatchCandidate` containing:

```text
work_session_id
decision_id
reliance_id
source_revision_id
source locator
```

If a canonical `WatchSink` is supplied, it may register that candidate in the active watch subsystem and return the external watch reference.

Only durable `used=yes` reliance enters this watch lane. `used=no`, `used=uncertain`, and discovered/fetched/exposed-but-unused inputs remain archive-only by default and consume no active watch obligation.

## 8. Agent protocol envelope

`testamur.agent_protocol` defines `testamur-agent-protocol-v1` and host-neutral event types:

```text
SOURCE_DISCOVERED
SOURCE_FETCHED
SOURCE_INSPECTED
CONTEXT_EXPOSED
SOURCE_EXPLICITLY_REFERENCED
SESSION_COMPLETED
SESSION_ABORTED
```

Protocol version mismatch is rejected explicitly. Host integrations may map native hooks, MCP/tool wrappers, browser capture, or local wrappers into these events. The event protocol carries only observable tool/session facts; it has no representation for hidden chain-of-thought or an assertion that the model reasoned from exposed text.

## 9. Persistence and identity

W4 storage is local SQLite and append-only. Tables cover:

```text
WorkSession identity
lifecycle events
input candidates
capture observations
reconciliation run
decisions
canonical reliance export receipts
watch candidates
external watch export receipts
```

Update/delete triggers reject mutation. New W4 IDs use deterministic `tst:*` IDs derived from canonical JSON and SHA-256. W4 has no runtime import from `witness.*`.

## 10. Integration requests

### W3 / canonical reliance owner

Implement an adapter satisfying `RelianceSink` that turns `RelianceCommitRequest` into the canonical immutable reliance receipt. The resulting receipt should preserve the W4 decision/session IDs as provenance and return its canonical `reliance_id`.

W4 intentionally does not infer policy admission, assurance selection, topology, or blast-radius semantics; those remain W3 responsibilities.

### W1 / convergence + product integration

Wire the canonical W3 reliance adapter and Testamur watch store behind W4's `RelianceSink` / `WatchSink`. Add WorkSession to the product read/API surface and expose explicit reconciliation state, pending reliance exports, archive-only inputs, and active watch candidates.

Do not translate `EXPOSED_TO_MODEL` into reliance in product glue.

### Agent/plugin integrations

Adapters should record exact SourceRevision IDs and evidence refs whenever available. If a host cannot establish exact revision identity, preserve the observation at the lower-fidelity/discovery boundary rather than inventing one.

## 11. E2E gate

The minimum cross-worker gate is:

```text
WorkSession OPEN
→ source discovered
→ exact revision fetched/inspected
→ optionally exposed/referenced
→ WorkSession complete
→ explicit yes/no/uncertain reconciliation
→ yes exported to canonical durable reliance
→ watch candidate created only for yes
→ later upstream revision change
→ W3/W1 reliance impact/blast-radius path identifies the exact downstream object
```

The first half is W4-owned. Upstream change propagation after the canonical reliance receipt is created is an integration gate with W3/W1.
