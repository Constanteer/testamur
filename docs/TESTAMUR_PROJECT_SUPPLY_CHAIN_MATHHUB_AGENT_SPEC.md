# Testamur Existing-Project Supply Chain + MathHub Agent Integration

Status: canonical implementation spec for the Testamur 1.0 launch line.

## 1. Scope

This document defines two product surfaces that must share Testamur's existing semantic model rather than creating parallel truth models:

1. continuous supply-chain inspection for an existing Testamur Project; and
2. human/agent interaction with MathHub through a reusable client/CLI/MCP boundary.

It also records launch-critical hosted-account requirements that must remain separate from Testamur evidence semantics.

## 2. Semantic invariants

All implementations MUST preserve:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
EXPOSED_TO_MODEL != RELIED
lineage != affectedness verdict
exact identity overlap != affectedness verdict
email ownership verified != source/content verified
```

No generic trust score is introduced by this work.

## 3. Existing Project repository binding

A Project is a container, not a Source and not a repository revision.

A Project MAY have one or more repository bindings. A binding records where scanner input can be obtained; it does not imply that every file in the repository is relied upon.

Canonical initial binding kinds:

- `local-path`: a normalized local directory path available to the current Testamur runtime.
- `git`: repository URL plus optional branch/ref metadata. Materialization/fetch policy is implementation-specific and MUST record the exact revision actually scanned before remote git scanning is claimed as exact.

A binding MUST have stable identity and recorded history. Rebinding a Project MUST NOT erase earlier scan provenance.

Initial CLI:

```text
testamur product project bind-repo PROJECT PATH
testamur product project repo PROJECT
testamur product project scan PROJECT
testamur product project supply-chain PROJECT
testamur product project supply-chain-diff PROJECT [--from REV] [--to REV]
```

`project import PATH --name NAME` remains a convenience path. For an existing Project, explicit `PROJECT` references are preferred over name matching.

## 4. Supply-chain scan lifecycle

Each scan is immutable evidence about the manifests observed at scan time.

Supported initial manifests remain:

- `requirements*.txt`
- `uv.lock`
- `poetry.lock`
- `package-lock.json`
- `npm-shrinkwrap.json`
- `Cargo.lock`
- `go.sum`

A repeated scan with identical canonical statements MUST be idempotent.

A changed scan MUST append a new `supply-chain-scan` RecordRevision. Project projection MUST select the newest valid scan revision only.

The scanner MUST preserve exact local manifest bytes through SHA-256 evidence. Declared package versions that lack exact artifact digests remain declared-version identity, not exact content identity.

## 5. Supply-chain diff

Diffing is mechanical and revision-scoped.

The diff MUST distinguish at minimum:

- dependency added;
- dependency removed;
- dependency revision/version changed;
- manifest added;
- manifest removed;
- manifest bytes changed;
- identity strengthened or weakened when digest/locator evidence changes.

A diff MUST NOT call any changed dependency vulnerable, invalid, unsafe, or broken.

Recommended schema:

```text
testamur.supply-chain.diff.v1
  from_scan_revision_id
  to_scan_revision_id
  dependencies:
    added[]
    removed[]
    changed[]
  manifests:
    added[]
    removed[]
    changed[]
  semantics:
    mechanical_only = true
    changed_implies_invalid = false
```

## 6. Advisory ingestion and affectedness

Provider documents are immutable adverse-event evidence.

Initial adapters:

- OSV
- CISA KEV

Provider version/range statements MUST NOT directly become Testamur affectedness verdicts. Resolution path:

```text
provider advisory revision
  -> normalized upstream identity/evidence
  -> exact identity resolution when available
  -> candidate overlap
  -> lineage/applicability evidence
  -> affectedness assessment
  -> impact
  -> targeted revalidation
```

Automated feed ingestion MAY create/update advisory event revisions, but it MUST preserve source provenance and provider identity.

## 7. Project refresh behavior

`project refresh` currently refreshes monitors. It MUST NOT silently grow a second meaning.

Preferred explicit operations:

- `project scan`: rescan bound repository supply-chain evidence.
- `project refresh`: refresh project monitors.
- a future `project refresh --all` MAY orchestrate both, but MUST return separate monitor and scan results.

Scheduled rescans SHOULD be implemented as an explicit project scanner schedule rather than pretending dependency manifests are ordinary Sources.

## 8. Agent / MCP supply-chain surface

Agent tools are thin projections over the same canonical service/CLI behavior.

Required initial tools:

```text
testamur.project_supply_chain
testamur.project_scan
testamur.project_supply_chain_diff
testamur.project_advisories
testamur.project_revalidate
```

Write tools MUST return structured evidence and MUST NOT accept caller-supplied affectedness verdicts or trust scores.

## 9. MathHub client boundary

MathHub remains a non-AI mathematical registry/argument graph. Lean remains the verifier.

The existing HTTP API becomes the authority behind a reusable `MathHubClient`. CLI and MCP call the same client rather than reimplementing API semantics.

Initial human CLI:

```text
mathhub search QUERY
mathhub claim CLAIM
mathhub argument CLAIM
mathhub path CLAIM --target TARGET [--via CLAIM]
mathhub graph [--claim CLAIM]
mathhub import DECLARATION
mathhub import-closure DECLARATION
mathhub claim add ...
mathhub proof add CLAIM ...
mathhub proof build PROOF
```

Initial MCP/plugin tools:

```text
mathhub.search_claims
mathhub.get_claim
mathhub.get_argument
mathhub.find_path
mathhub.get_graph
mathhub.import_declaration
mathhub.import_closure
mathhub.register_claim
mathhub.register_proof
mathhub.build_proof
```

Read tools MAY be enabled by default. Mutating/import/build tools SHOULD be clearly identified as writes and preserve MathHub's exact Lean environment/build provenance.

AI-generated prose or proof suggestions are not MathHub verification. A successful Lean Build is the verification witness.

## 10. Plugin architecture

The Codex plugin may expose both Testamur and MathHub tools, but the packages remain thin adapters:

```text
Codex / Claude Code / OpenCode / other MCP host
                 |
        host adapter / MCP
          /             \
 Testamur client      MathHub client
       |                  |
 Testamur core       MathHub HTTP API
                          |
                         Lean
```

Host lifecycle capture remains Testamur-specific. MathHub interaction does not create hidden-reasoning capture.

## 11. MathHub repository cleanup

MathHub MUST stop shipping stale Testamur runtime/package copies once the corresponding canonical Testamur functionality lives in `Constanteer/testamur` and `Constanteer/testamur-plugins`.

Cleanup is staged:

1. add/verify MathHub-native package/client/CLI/tests;
2. remove obsolete Testamur scripts/docs/plugin copies from MathHub;
3. keep compatibility only where deployment currently imports it, then remove after host pin migration.

Do not delete code solely because its name looks stale; verify runtime/deployment references first.

## 12. Hosted email ownership verification

Hosted account email verification is launch-critical account security, but semantically separate from Testamur evidence verification.

Required behavior:

- signup creates an account in `pending_verification` state;
- generate a cryptographically random, single-use token;
- store only a token digest;
- token has an explicit expiry;
- resend is rate-limited and invalidates/supersedes older active tokens as defined by implementation;
- verification endpoint consumes the token atomically;
- sign-in/session policy clearly distinguishes unverified users;
- high-value hosted workspace mutation is unavailable until email ownership is verified;
- verification mail delivery failures do not mark the account verified;
- logs never contain raw verification tokens.

Public account payloads expose `email_verified` / verification state without exposing token material.

The term "verified email" MUST NOT be reused to imply Testamur Source, Record, Claim, Proof, advisory, or project verification.

## 13. Release gates

Before calling these surfaces launch-ready:

- regression proving Project projection returns newest supply-chain scan after at least two changed scans;
- repeated unchanged scans remain idempotent;
- dependency add/remove/version-change diff tests;
- explicit Project repository binding tests;
- agent/MCP tool contract tests;
- MathHub CLI/client tests against the HTTP contract;
- clean-host plugin first-run smoke;
- hosted signup -> email sent -> verify -> sign in/workspace mutation smoke;
- CI absence/unavailability is recorded as unavailable, never reported as green.
