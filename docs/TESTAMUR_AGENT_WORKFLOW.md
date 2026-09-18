# Testamur Agent Workflow — Passive Capture, Reliance Reconciliation, Monitoring, and Attestation

> **Status:** product / protocol direction for integrating Testamur into AI-assisted work environments such as Codex, OpenCode, IDE agents, browser agents, CLIs, and future instrument adapters.
>
> This document defines the primary workflow surface that turns ordinary AI-assisted work into inspectable provenance without requiring the user to manually construct a knowledge graph first.

---

## 1. Product thesis

Testamur should live where work already happens.

The primary adoption loop is not:

```text
open Testamur
→ manually create records
→ manually attach evidence
→ manually construct dependency graph
```

The preferred loop is:

```text
use AI normally
→ Testamur passively records source/work events
→ agent finishes task
→ optional reliance reconciliation
→ relied-on inputs become active monitored dependencies
→ unused-but-observed inputs remain archived provenance
→ resulting project/artifact may be pushed private, organizational, or public
→ Testamur can issue a provenance/assurance attestation over the recorded chain
```

The public website is therefore the GUI and network surface of a provenance system whose capture happens primarily inside agent workflows.

A compact formulation is:

> **Capture the work automatically; ask for epistemic commitment only when it matters.**

---

## 2. Scope and non-goals

This document covers:

```text
agent/plugin capture
WorkSession lifecycle
source observation
artifact/work observation
reliance reconciliation
watch vs archive routing
project supply-chain scanning
upstream monitoring
attestation generation
private/public publication
human-mediated access for protected sources
instrument/device adapter direction
```

This document does **not** redefine:

```text
Source / SourceRevision identity
Testamur Core object identity
revision DAG semantics
verification semantics
attestation cryptography
content-rights policy
commerce / subscription semantics
```

Existing owners remain authoritative.

---

## 3. Core workflow

The target end-to-end flow is:

```text
Codex / OpenCode / IDE Agent / Browser Agent
                    │
                    ▼
              Testamur plugin
                    │
          passive event capture
                    │
                    ▼
              WorkSession S
                    │
        ┌───────────┴────────────┐
        │                        │
        ▼                        ▼
 source activity             work activity
 search / fetch / read       files / commands /
 docs / repos / APIs         patches / builds /
 papers / datasets           tests / artifacts
        │                        │
        └───────────┬────────────┘
                    ▼
             task completion
                    │
          reliance reconciliation
                    │
       ┌────────────┴────────────┐
       ▼                         ▼
    RELIED_ON                 NOT_RELIED_ON
       │                         │
       ▼                         ▼
  monitor / watch            archive only
  revalidate                 preserve receipt
  blast radius               no recurring checks
       │                         │
       └────────────┬────────────┘
                    ▼
               Testamur push
                    │
        local / private / org / public
                    │
                    ▼
             optional attestation
```

The workflow must remain useful even when the user never opens the Testamur web UI during the task.

---

## 4. WorkSession

### 4.1 Role

`WorkSession` is an operational provenance envelope for one bounded unit of human/agent work.

It is **not** a truth object and must not itself imply that any output is correct.

Examples:

```text
"Implement OAuth refresh flow"
"Compare three supplier specifications"
"Derive and verify theorem X"
"Analyze experiment run 2026-09-14-A"
"Prepare a regulatory summary"
```

A WorkSession groups observations that otherwise arrive as disconnected tool events.

### 4.2 Suggested identity

```text
work_session_id
project_ref                 optional
workspace_ref               optional
started_at
ended_at                    optional while active
initiating_actor_ref
agent_ref                   optional
agent_version               optional
host_environment
capture_policy_ref
reconciliation_policy_ref
visibility
```

Suggested status lifecycle:

```text
OPEN
COMPLETED_UNRECONCILED
RECONCILED
PUSHED
ATTESTED
ABORTED
```

These are workflow states, not epistemic states.

### 4.3 Session contents

A WorkSession may reference:

```text
search observations
fetch observations
exact SourceRevisions
context exposures
explicit citations/references
commands executed
files read
files modified
commits produced
artifacts produced
verification/test runs
agent declarations
human confirmations
project objects created/revised
attestations produced
```

The session should preserve references to canonical records owned elsewhere instead of duplicating their semantics.

---

## 5. Capture adapter model

Testamur should support several integration levels because no single agent ecosystem can be assumed to expose identical hooks.

### 5.1 Native plugin

Preferred integration where the host exposes sufficient lifecycle and tool hooks.

Examples:

```text
Codex plugin / integration
OpenCode plugin
IDE extension
agent-specific extension
```

A native plugin should observe, where available:

```text
task start/end
search call
fetch/open/read call
browser navigation
download
repo/file read
shell command
file write / patch
build / test invocation
artifact creation
agent final response
```

### 5.2 Tool/protocol wrapper

When native hooks are unavailable, wrap the tools the agent uses.

Examples:

```text
MCP server
HTTP fetch proxy
search wrapper
filesystem wrapper
shell execution wrapper
Git wrapper
SDK instrumented client
```

The wrapper should capture observable tool events without pretending to capture internal model reasoning.

### 5.3 Fallback local capture

Fallback modes may include:

```text
CLI session wrapper
local daemon
browser extension
filesystem watcher
Git hook
explicit `testamur capture` commands
```

Fallback capture is lower fidelity and should declare that limitation.

---

## 6. Capture semantics

The plugin must preserve the distinction between observation and interpretation.

### 6.1 Source lifecycle

The preferred progression reuses the existing source-usage semantics:

```text
DISCOVERED
FETCHED / INSPECTED
EXPOSED_TO_MODEL
EXPLICITLY_REFERENCED
RELIED_ON_BY_PROJECT_OBJECT
```

No automatic promotion is allowed.

Examples:

```text
search result appeared
    -> DISCOVERED

agent opened exact webpage bytes
    -> FETCHED

content was inserted into model context
    -> EXPOSED_TO_MODEL

agent final answer cited it
    -> EXPLICITLY_REFERENCED

agent/human declares a project decision or artifact actually relied on it
    -> RELIED_ON_BY_PROJECT_OBJECT
```

### 6.2 Capture does not prove cognition

If a host reports that source revision R entered the model context, Testamur may record:

```text
EXPOSED_TO_MODEL(R)
```

It must not infer:

```text
THE_MODEL_REASONED_FROM(R)
```

unless a later explicit declaration or other admissible evidence supports that relation.

### 6.3 Exact version rule

Whenever possible, source usage must bind to an exact `SourceRevision` rather than a locator.

```text
valid:
artifact A --relies_on--> SourceRevision R7

insufficient:
artifact A --relies_on--> https://example.com/docs
```

The locator remains useful for future revalidation but does not replace revision identity.

---

## 7. Reliance reconciliation

### 7.1 Purpose

Most agent sessions inspect more material than they actually use.

Testamur should avoid treating every fetched source as a durable dependency.

At task completion, a configurable reconciliation phase asks which observed inputs materially influenced the final work.

### 7.2 User policy

Suggested modes:

```text
TRUST_AGENT_DECLARATION
ASK_USER_TO_CONFIRM
MECHANICAL_ONLY
DISABLED
```

Default for low-friction individual use may be `TRUST_AGENT_DECLARATION`.

The selected policy must be stored with the resulting declarations.

### 7.3 Agent reconciliation request

A host integration may present the agent with a structured table of candidate inputs:

```text
source revision
locator / title
when fetched
whether exposed
whether explicitly referenced
optional evidence regions
```

The agent is asked to return, per candidate:

```text
used: yes | no | uncertain
relation_type
used_for
project_object_ref         optional
exact_region_refs          optional
notes                      optional
```

Example:

```json
{
  "source_revision": "src_rev_0194",
  "used": "yes",
  "relation_type": "depends_on",
  "used_for": "API retry behavior implemented in src/client.ts"
}
```

### 7.4 Declaration semantics

An accepted agent answer must retain provenance such as:

```text
declaration_class = DECLARED_BY_AGENT
agent_ref
agent_version
work_session_id
reconciliation_policy
created_at
```

A trusted agent declaration may be accepted operationally without being relabeled as mechanically observed fact.

The invariant is:

```text
agent declared reliance
!=
Testamur mechanically proved internal reasoning used the source
```

### 7.5 Human confirmation

Where policy requires confirmation, the UI should allow batch acceptance rather than forcing one modal per source.

Suggested actions:

```text
Accept all declared relied-on
Reject selected
Mark uncertain
Change relation type
Attach to another project object
```

---

## 8. Watch lane and Archive lane

Reconciliation produces two operational lanes.

### 8.1 Watch lane

Inputs with durable reliance become active upstream dependencies.

Typical behavior:

```text
exact SourceRevision retained
source identity retained
revalidation policy attached
scheduled/on-access checks enabled
new upstream revision detected
change event emitted
blast radius calculated from durable reliance
affected project objects surfaced for review
```

`CHANGED` must not mechanically mean `INVALID`.

Instead:

```text
upstream changed
→ prior reliance may require review
→ downstream impact is potential impact
```

### 8.2 Archive lane

Inputs observed during the session but not declared relied upon remain provenance history without ongoing monitoring by default.

Archive lane may retain, subject to rights and storage policy:

```text
source identity
retrieval receipt
revision digest
retained bytes or content reference
exposure record
session association
```

It should not consume ordinary recurring watch capacity unless the user later promotes it.

### 8.3 Promotion and demotion

Users or later workflows may promote an archived source into active reliance if later work actually depends on it.

A relied-on source may cease to be an active dependency only through explicit relation lifecycle/retraction semantics; its historical role remains preserved.

---

## 9. Project ingestion and upstream supply-chain scanning

Testamur must also work when no agent session exists.

A user may connect or import a project directly.

### 9.1 Project inputs

Initial adapters may inspect:

```text
Git repository
package manifests / lockfiles
container definitions
CI workflows
submodules
model manifests
external datasets
explicit documentation links
API endpoints
standards/specification references
licenses
artifact registries
```

Examples:

```text
package.json / package-lock.json
pyproject.toml / requirements.txt
Cargo.toml / Cargo.lock
go.mod
Dockerfile / image digest
GitHub Actions workflows
model/config manifests
```

### 9.2 Dependency graph

The project importer may establish mechanically justified dependency relations where the source format supports them.

Example:

```text
Project P
 ├── depends_on package A@1.4
 │      └── distributed_from registry artifact X
 ├── uses container image D@sha256:...
 └── references API documentation SourceRevision R7
```

Do not convert heuristically discovered adjacency into durable reliance without preserving how it was inferred.

### 9.3 Upstream traversal budgets

Recursive supply-chain expansion must be bounded.

Suggested controls:

```text
max_depth
max_objects
max_external_fetches
allowed registries/domains
include_dev_dependencies
include_transitive_dependencies
```

Default traversal should be conservative enough to avoid exploding an npm/PyPI/container dependency graph unintentionally.

### 9.4 Continuous monitoring

Once dependencies are accepted, Testamur may monitor relevant upstream state:

```text
new package release
repository revision
source document revision
API specification revision
container digest change
standard/regulation revision
model checkpoint replacement
```

Only dependency kinds with clear update semantics should receive automatic monitoring.

---

## 10. Produced artifacts and work outputs

A WorkSession may produce one or more artifacts:

```text
code patch
Git commit
binary
container image
report
proof
simulation result
dataset
model output
CAD artifact
configuration
```

For each artifact, Testamur should record exact identity where possible:

```text
artifact_ref
content digest
media/type
created_at
producing session
project revision
```

A project relation can then state:

```text
Artifact A
  produced_by WorkSession S
  relies_on SourceRevision R7
  derived_from Dataset D3
  verified_by TestRun T9
```

`produced_by` and `verified_by` are not synonyms.

---

## 11. Attestation / provenance credential

### 11.1 Purpose

Testamur may generate a portable attestation describing the recorded conditions under which an artifact or project state was produced.

The attestation should prove recorded provenance and verification facts, not universal correctness.

### 11.2 Candidate contents

```text
subject
  artifact / project revision digest

work session
  session id
  actor / agent identity where recorded
  host environment

relied-on inputs
  exact SourceRevision refs
  repository commits
  package/artifact digests
  datasets
  other project objects

reconciliation
  policy
  agent declarations
  human confirmations if any

verification
  tests
  builds
  formal proof checks
  reproduction records
  domain verifiers

policy
  policy id / revision

provenance root / evidence root

timestamp

issuer/signature
```

### 11.3 Semantics

A valid attestation may support a statement such as:

> Artifact A was produced in recorded WorkSession S, under policy P, with these exact declared inputs and these exact verification receipts.

It must not automatically support:

> Artifact A is correct.

or:

> Every internal model reasoning step is fully captured.

### 11.4 Assurance profile

Different users may define stricter profiles.

Example:

```text
profile: agent-assisted-code-v1

requires:
- all network fetches captured by gateway
- final relied-on sources reconciled
- artifact content digest
- build success
- test suite success
- no currently stale required source under policy
```

Another profile may require human review or independent verification.

Profiles must remain explicit policy, not global Testamur truth ranks.

---

## 12. Private, organizational, and public publication

A session/project may remain:

```text
LOCAL
PRIVATE
ORG_SHARED
METADATA_ONLY
PUBLIC
```

Publishing later must preserve exact historical lineage.

Example:

```text
private WorkSession
      ↓
private project state
      ↓
commitment / attestation
      ↓
selected disclosure
      ↓
public artifact + public provenance subset
```

Selective disclosure may reveal:

```text
artifact digest
input commitments
verification receipts
policy revision
attestation signature
```

while withholding:

```text
private source bytes
private prompts
internal notes
private repository content
confidential datasets
```

A commitment proves continuity with committed state, not truth.

---

## 13. Human-mediated access for CAPTCHA / authentication / anti-bot boundaries

Testamur must not bypass CAPTCHA or access controls.

When automated capture encounters a legitimate human-access boundary, the expected flow is:

```text
automated retrieval attempted
        ↓
CAPTCHA / interactive auth / access challenge
        ↓
NEEDS_HUMAN_ACCESS
        ↓
user opens legitimate browser flow
        ↓
user completes challenge/authentication
        ↓
Testamur browser integration captures policy-permitted resulting content
        ↓
SourceRevision + RetrievalReceipt
```

The receipt should record the access class, for example:

```text
access_method = human_mediated_authenticated_capture
```

without persisting credentials or authentication secrets.

If Testamur reaches sufficient adoption, official machine-access or verified-agent partnerships with source/platform providers should be preferred over attempts to evade access controls.

---

## 14. Experimental and physical-instrument adapters

Long-term Testamur provenance should extend beyond software/web sources.

An instrument adapter does not need to teach Testamur the entire scientific domain. It needs to produce stable provenance records.

Suggested adapter output:

```text
instrument identity
instrument model
firmware/software revision
calibration identity/state
run id
start/end timestamp
operator / automation actor
protocol/configuration
raw output artifact digests
environmental metadata where available
adapter id/version
```

This enables chains such as:

```text
Instrument
  ↓ produces
Measurement Run
  ↓ produces
Dataset
  ↓ analyzed_by
Analysis
  ↓ supports
Claim
  ↓ published_as
Paper
```

Initial integrations should be open and generic:

```text
folder watcher
CLI/SDK
JSON/CSV sidecar
HTTP callback
lab export importer
```

Vendor-native integrations can follow when real usage justifies them.

---

## 15. Plugin event protocol

A minimal portable event protocol should allow host integrations to emit events without importing all internal Testamur implementation details.

Suggested envelope:

```json
{
  "protocol": "testamur-agent-events-v0",
  "event_id": "...",
  "session_id": "...",
  "timestamp": "...",
  "kind": "source.fetch",
  "actor": {...},
  "payload": {...}
}
```

Candidate event kinds:

```text
session.started
session.completed

source.discovered
source.fetch_started
source.fetch_completed
source.inspected
source.exposed_to_model
source.explicitly_referenced

command.executed
file.read
file.modified
artifact.produced
verification.recorded

reconciliation.started
reliance.declared
reliance.confirmed
reliance.rejected
reconciliation.completed

project.pushed
attestation.created
```

Events should be append-only/idempotent by `event_id`.

Repeated identical delivery is a no-op; conflicting reuse of an event ID fails closed.

---

## 16. Privacy defaults

Passive capture can easily become invasive if the boundary is unclear.

Default rules should include:

```text
no password / auth-header capture
no secret environment-variable persistence
no automatic cloud publication
no prompt/content upload merely because local capture occurred
no private repository publication without explicit policy
no cross-workspace deduplication that leaks private object existence
```

The host adapter should support allow/deny filters for:

```text
domains
paths
file globs
tool kinds
content classes
workspace roots
```

Users should be able to disable raw-content retention while retaining hashes/receipts where useful.

---

## 17. Failure and partial-observability semantics

The system must represent gaps explicitly.

Examples:

```text
source fetched outside Testamur gateway
    -> source use may be UNOBSERVED

host reports URL but not bytes
    -> locator observed; exact revision unresolved

agent declines reconciliation
    -> session COMPLETED_UNRECONCILED

agent marks source uncertain
    -> declaration remains uncertain; do not promote to durable relied-on by default

revalidation fails
    -> REVALIDATION_FAILED, not UNCHANGED

artifact changed after attestation
    -> old attestation remains bound to old digest
```

A low-fidelity integration should never fabricate full provenance merely to satisfy a UI.

---

## 18. Early UI implications

The signed-in Testamur home should increasingly organize around work rather than empty configuration.

Example:

```text
Recent work
────────────────────────────────────────
Implement OAuth refresh flow       Reconciled
Supplier comparison                Needs review
Experiment 14-A                    Attested

Upstream changes
────────────────────────────────────────
3 relied-on sources changed
1 package revision requires review

Active watch
────────────────────────────────────────
42 relied-on upstream objects
```

A WorkSession page may expose:

```text
Overview
Sources
Work / Artifacts
Reliance
Verification
Attestation
Timeline
```

The page should visually distinguish:

```text
observed
agent-declared
human-confirmed
mechanically verified
```

---

## 19. Early launch scope

The first agent-workflow implementation should remain narrow.

### Phase A — local capture

```text
WorkSession
source fetch capture
exact SourceRevision binding
file/command/artifact event capture
local session timeline
```

### Phase B — reconciliation

```text
agent reliance questionnaire
TRUST_AGENT_DECLARATION policy
optional human confirmation
Watch vs Archive routing
```

### Phase C — project integration

```text
Git project import
basic dependency manifest scanning
bounded upstream traversal
watch relied-on upstreams
blast-radius link back to project objects
```

### Phase D — attestation

```text
artifact digest
session provenance bundle
input commitments
verification receipts
portable signed attestation
private/public disclosure modes
```

### Phase E — ecosystem adapters

```text
browser extension
MCP/tool wrappers
additional coding agents
CI integration
artifact registries
lab/instrument adapters
```

---

## 20. Minimum acceptance scenarios

An implementation should not claim this workflow until at least the following scenarios work end-to-end.

### Scenario A — coding agent uses two docs and ignores one

```text
agent searches 5 candidates
fetches 3
2 enter context
agent declares 1 materially relied upon

result:
- 1 exact SourceRevision enters Watch lane
- 2 fetched-but-unrelied observations remain archived
- produced code artifact links to the relied-on revision
```

### Scenario B — upstream source changes later

```text
artifact A relied on SourceRevision R1
same source later yields R2

result:
- R1 remains unchanged historical provenance
- R2 is recorded separately
- source emits CHANGED
- artifact/project appears in potential blast radius
- Testamur does not assert artifact A is false/invalid automatically
```

### Scenario C — incomplete capture

```text
host reports that agent visited a URL
exact bytes are unavailable

result:
- locator observation can be retained
- no exact SourceRevision reliance is fabricated
- reconciliation cannot silently upgrade unresolved content to exact evidence
```

### Scenario D — project import

```text
connect Git repository
lockfile names direct dependencies
bounded depth-2 traversal enabled

result:
- direct package revisions are imported with provenance
- transitive expansion stops at configured budget
- provenance records distinguish manifest-declared from externally fetched metadata
```

### Scenario E — attestation

```text
artifact produced
relied-on source reconciled
build and tests recorded
attestation requested

result:
- attestation binds exact artifact digest
- exact input revisions are listed/committed
- reconciliation policy is included
- test/build receipts are included
- attestation does not claim universal correctness
```

### Scenario F — protected source

```text
automated fetch encounters CAPTCHA/auth challenge
user completes legitimate browser access
capture resumes through browser integration

result:
- no bypass occurs
- credentials are not serialized
- receipt records human-mediated authenticated access
- resulting exact content may enter provenance subject to rights policy
```

---

## 21. Design laws

1. **Work capture should be passive; reliance should be explicit.**
2. **Fetched is not relied upon.**
3. **Exposed to a model is not proof of cognitive use.**
4. **Agent declarations may be operationally trusted while remaining declarations.**
5. **Durable dependencies must point to exact revisions whenever exact identity is available.**
6. **Relied-on inputs receive monitoring; unused observations default to archive.**
7. **Upstream change creates review/impact state, not automatic falsity.**
8. **Attestations prove recorded provenance and checks, not universal correctness.**
9. **Private capture never implies cloud publication.**
10. **CAPTCHA/authentication boundaries are human-mediated or provider-integrated, never bypassed.**
11. **Project dependency scanning is bounded and provenance-preserving.**
12. **Physical instruments join through provenance adapters, not a forced universal laboratory ontology.**
13. **Low-fidelity integrations must expose missing observability rather than fabricate complete provenance.**
14. **The web UI is a projection of captured work, not the only place where Testamur state can originate.**

---

## 22. North-star workflow

The long-term product loop is:

```text
WORK
 ↓
AI / HUMAN
 ↓
search / fetch / build / test / measure
 ↓
PASSIVE CAPTURE
 ↓
WORK SESSION
 ↓
RELIANCE RECONCILIATION
 ↓
DEPENDENCY GRAPH
 ↓
WATCH + REVALIDATE
 ↓
UPSTREAM CHANGE
 ↓
BLAST RADIUS
 ↓
REVIEW / RERUN
 ↓
ARTIFACT / PROJECT STATE
 ↓
ATTESTATION
 ↓
PRIVATE / ORG / PUBLIC NETWORK
```

The intended user experience is simple:

> **Do the work where you already work. Testamur preserves what the work depended on, keeps watching those dependencies, and can later show exactly what justified the result.**
