# Testamur Authority / Capability Graph

> **Status:** canonical implementation specification for authority, credential, trust-boundary and delegated-capability reachability.
>
> This model is intentionally distinct from material lineage and epistemic reliance:
>
> ```text
> lineage:    what came from what?
> reliance:   what work actually depends on what?
> authority:  what principal or runtime can cause, access or delegate what?
> ```
>
> The graphs may be joined for impact analysis, but they must not be silently collapsed into one relation vocabulary.

## 1. Motivation

A software supply-chain incident is not bounded by package dependency edges.

A compromised parser may expose a process credential. That credential may be accepted by another service. The resulting session may inherit a connector. The connector may have access to a code repository. None of those authority transitions is accurately represented by `DERIVED_FROM`, `CONTAINS`, or generic dependency edges.

Canonical motivating shape:

```text
untrusted input
  -> vulnerable parser / runtime
  -> process compromise
  -> readable credential
  -> token accepted by identity service
  -> authenticated service session
  -> delegated connector
  -> repository capability
```

The security question is:

> If subject X is fully compromised under an explicit compromise model, what authority can become reachable, through which evidence-backed transitions, across which trust boundaries?

Testamur must answer that question without claiming more than the evidence establishes.

## 2. Hard semantic boundaries

These remain non-negotiable:

```text
lineage != authority
reliance != authority
network reachability != authorization
credential presence != credential usability
token acceptance != unlimited scope
authentication != authorization
connector attachment != connector permission
permission != successful action
declared permission != observed permission
reachable != compromised
compromised upstream != compromised downstream
```

Authority propagation is therefore evidence-bearing and relation-specific.

A path through the graph establishes only the authority implied by the exact edges on that path.

## 3. Canonical objects

The authority graph operates over exact durable references. Implementations may project existing Testamur objects into these roles; they must not invent a parallel identity universe.

### 3.1 AuthoritySubject

An entity that can possess, expose, delegate or exercise capability.

Examples:

- process or container revision;
- workload/service identity;
- human account;
- authenticated session;
- agent runtime;
- connector installation;
- credential/token revision;
- repository/project/cloud resource;
- network endpoint.

Every subject must have stable identity. Revision-sensitive subjects should use exact revision identity where relevant.

### 3.2 Capability

A normalized permission or effect.

Canonical capability shape:

```json
{
  "namespace": "github",
  "action": "pull_request.write",
  "resource": "repo:openai/openai",
  "constraints": {}
}
```

Capabilities are not global strings. They must include a namespace and should identify a resource or resource class when known.

Examples:

```text
filesystem.read:/run/secrets/*
oauth.exchange:audience=codex
service.authenticate:codex
github.repo.read:repo/X
github.pull_request.write:repo/X
aws.s3.get_object:bucket/Y/*
network.connect:host:port
process.exec:container/Z
```

Unknown or provider-specific permissions may use namespaced extension identifiers.

### 3.3 Credential

A credential is modeled as an authority-bearing subject, not merely opaque metadata.

Relevant fields may include:

- credential kind;
- issuer;
- subject/principal;
- audience;
- scopes;
- expiration;
- binding constraints;
- proof-of-possession requirements;
- source revision;
- revocation state observation.

Secret bytes must not be stored merely to represent authority.

### 3.4 TrustBoundary

A named boundary crossed by an authority edge.

Examples:

- internet -> community workload;
- community workload -> identity plane;
- identity plane -> employee product session;
- product session -> GitHub connector;
- connector -> private repository.

Boundary labels are evidence/analysis metadata, not proof of compromise.

## 4. Authority relations

The first canonical relation set is:

```text
CAN_READ
CAN_WRITE
CAN_EXECUTE
CAN_CONNECT
CAN_IMPERSONATE
CAN_AUTHENTICATE_AS
ACCEPTS_CREDENTIAL
ISSUES_CREDENTIAL
DELEGATES
GRANTS
HAS_CAPABILITY
BOUND_TO
EXPOSES
```

These relations are directional unless explicitly documented otherwise.

### CAN_READ

`A --CAN_READ--> B`

A compromise of A may permit reading B, subject to edge constraints.

Typical use: workload can read a mounted token or secret.

### CAN_WRITE

A may mutate the target or a defined target surface.

### CAN_EXECUTE

A can cause code/process execution in the target execution context.

### CAN_CONNECT

A can establish transport-level communication to a target endpoint.

This never implies authentication or authorization.

### CAN_IMPERSONATE

A possesses authority sufficient to act as another principal under the modeled mechanism.

This must not be inferred merely from account/session adjacency.

### CAN_AUTHENTICATE_AS

A credential/session can authenticate as a specific principal or principal class.

### ACCEPTS_CREDENTIAL

`service --ACCEPTS_CREDENTIAL--> credential-kind-or-instance`

Acceptance must preserve audience/scope/binding constraints. "Same SSO" does not imply cross-service acceptance.

### ISSUES_CREDENTIAL

Issuer to credential relation.

### DELEGATES

An authority-bearing subject delegates a bounded set of capabilities to another subject.

The delegated capability set must be explicit.

### GRANTS

A policy/role/authorization object grants a capability to a principal/session/connector.

### HAS_CAPABILITY

A subject directly possesses a capability according to explicit evidence.

### BOUND_TO

Represents binding constraints such as token-to-device, token-to-session, workload identity to pod, or connector to installation.

Binding constrains propagation; it is not itself authority.

### EXPOSES

A subject exposes another authority-bearing object to compromise, such as an environment variable, mounted secret, metadata credential endpoint, or browser session material.

Use `EXPOSES` only when exposure is established. Presence in the same deployment is insufficient.

## 5. Evidence classes

Authority edges require evidence.

Canonical evidence classes reuse the Testamur discipline:

```text
OBSERVED
DERIVED
DECLARED
```

Examples:

- OBSERVED: runtime inspection shows a mounted secret path is readable;
- DERIVED: analyzer parses an IAM policy and derives an effective permission;
- DECLARED: documentation states a connector has write access.

Derived evidence must identify analyzer and analyzer version.

Declared evidence must not be silently upgraded into observed effective authority.

An implementation may add confidence or freshness metadata, but must not collapse provenance class into a scalar trust score.

## 6. Edge constraints

Every authority edge may carry explicit constraints.

Canonical constraint fields include:

```text
audience
scope
resource
resource_pattern
principal
expires_at
network_zone
source_ip
device_binding
session_binding
mfa_required
approval_required
human_confirmation_required
time_window
condition
```

Unknown constraints remain unknown. Absence of recorded constraints must not be interpreted as unrestricted authority.

## 7. Compromise models

Reachability requires an explicit compromise model.

Initial models:

```text
READ_ONLY_COMPROMISE
PROCESS_CODE_EXECUTION
ACCOUNT_SESSION_TAKEOVER
CONNECTOR_TAKEOVER
CREDENTIAL_THEFT
FULL_SUBJECT_COMPROMISE
```

Each model defines which outgoing relation classes can be exercised.

Example:

- `READ_ONLY_COMPROMISE` may traverse `CAN_READ` and `EXPOSES`, but not `CAN_WRITE`;
- `PROCESS_CODE_EXECUTION` may exercise process-owned read/write/connect capabilities;
- `CREDENTIAL_THEFT` begins at a credential subject and evaluates where that credential is accepted;
- `FULL_SUBJECT_COMPROMISE` is intentionally strong and should be used explicitly.

No default query should silently assume maximal compromise.

## 8. Reachability algorithm

The canonical query is conceptually:

```python
authority_reachability(
    subject_ref,
    *,
    compromise_model,
    capability_filter=None,
    max_depth=...,
    max_paths=...,
    as_of=None,
)
```

The engine must:

1. start from an exact subject;
2. determine traversable outgoing authority relations under the selected compromise model;
3. apply edge constraints;
4. propagate only capability actually conveyed by the relation;
5. record trust-boundary crossings;
6. retain complete evidence basis for every returned path;
7. remain cycle-safe;
8. enforce explicit depth/path/expansion budgets;
9. report truncation rather than manufacture completeness;
10. preserve alternate paths.

A path is valid only if every transition is valid under its constraints.

## 9. Capability algebra

Authority does not compose by naive transitive closure.

Examples:

```text
CAN_CONNECT + ACCEPTS_CREDENTIAL
  may establish authenticated reachability
  only when credential audience/binding constraints match

session HAS_CAPABILITY github.repo.read
  does not imply github.repo.write

connector DELEGATES {repo.read, pr.write}
  propagates only those capabilities

CAN_READ secret
  does not imply secret is a credential
```

The implementation therefore needs relation-specific transition rules rather than a single generic graph walk.

Capability sets must be intersected with scopes/constraints at each delegation boundary.

## 10. Trust-boundary crossings

Authority paths should report boundary transitions separately from ordinary edges.

A path explanation should be able to render:

```text
community-image-worker
  -> exposed credential
  [boundary: community workload -> identity plane]
  -> Codex session
  [boundary: product session -> external connector]
  -> GitHub connector
  [boundary: connector -> private source repository]
  -> repo capability
```

Boundary count is descriptive. Testamur must not turn it into a universal risk score.

## 11. Authority blast radius

Authority blast radius answers:

> Given compromise of X under model M, which authority-bearing subjects, capabilities and protected resources become reachable?

Canonical output should include:

```text
starting_subject
compromise_model
reachable_subjects
reachable_capabilities
protected_resources
trust_boundary_crossings
paths
evidence_basis
truncated
unknowns
```

It must distinguish:

```text
reachable capability
!= observed malicious use
!= confirmed compromise of target
```

## 12. Joining authority with lineage and affectedness

The graphs join at exact subject/revision identity.

Example:

```text
CVE advisory
  -> affected libheif revision
  -> lineage / CONTAINS
  -> deployed image revision
  -> runtime process subject
  -> authority graph
  -> readable SSO credential
  -> authenticated Codex session
  -> delegated GitHub connector
  -> private repository capability
```

The join must remain explainable:

- affectedness establishes why the runtime may require reconsideration;
- authority establishes what the runtime could reach if compromised;
- neither fact proves exploitation occurred.

## 13. Credential and token semantics

Credential modeling must support at least:

- opaque bearer tokens;
- OAuth access tokens;
- refresh tokens;
- API keys;
- workload identity credentials;
- browser/session cookies;
- short-lived signed assertions.

Token analysis must preserve:

```text
issuer
subject
audience
scope
expiry
binding
revocation observation
delegation chain
```

A token valid for one audience must not be assumed valid for another.

A scope label must not be interpreted as effective permission without provider-specific semantics or observed evidence.

Secret material should be redacted or represented by digest/identity unless the user explicitly configures secure secret retention.

## 14. Agent and connector semantics

AI agents and connectors are authority-bearing runtimes.

A connector must be modeled separately from the user/session that attached it.

Example:

```text
employee-session
  --DELEGATES {repo.read, pr.write}-->
github-connector-installation
  --HAS_CAPABILITY-->
repo:private
```

High-impact operations may carry constraints such as:

```text
human_confirmation_required=true
approval_required=true
branch_protection=true
```

The graph records those constraints. It does not assume the control is bypassable.

## 15. Provider adapters

Authority ingestion should use provider-specific adapters that emit canonical evidence-bearing edges.

Expected future adapters include:

- GitHub App/OAuth installation permissions;
- cloud IAM policies;
- Kubernetes service-account/RBAC projections;
- OIDC/OAuth token metadata;
- CI/CD credentials and environments;
- secret mounts and workload environment observations;
- network policy/security-group reachability.

Provider adapters must fail closed when semantics are ambiguous.

## 16. Storage model

Authority data is append-only evidence.

Suggested canonical tables:

```text
testamur_authority_subjects
testamur_authority_edges
testamur_capabilities
testamur_authority_assessments
testamur_trust_boundaries
```

An authority edge should minimally pin:

```text
edge_id
relation_type
source_ref
target_ref
capability_json
constraints_json
evidence_json
boundary_ref
recorded_at
```

Updates create superseding observations/assessments rather than mutating historical truth.

## 17. Query and CLI surface

The implementation should converge toward:

```text
testamur authority show <subject>
testamur authority reach <subject> --model process-code-execution
testamur authority explain <path-or-result>
testamur authority blast-radius <subject> --model ...
```

For the existing compact CLI, aliases/projections may initially appear under `testamur impact`; however the semantic implementation must remain authority-specific.

Machine-readable output must expose evidence and truncation.

## 18. Product/Web projection

Project pages should eventually expose a security/reachability view that answers:

- what credentials/capabilities this workload can access;
- which external services trust them;
- which connectors inherit delegated authority;
- which protected resources are reachable;
- which trust boundaries are crossed;
- what changed since the previous observation.

The Web UI is a projection of canonical authority state, not a browser-only graph model.

## 19. Policy integration

Policy may assert constraints such as:

```text
image-processing workloads MUST NOT expose SSO credentials
internet-facing workloads MUST NOT reach production metadata services
community identities MUST NOT authenticate to employee products
agent connectors MUST be read-only by default
write capability to protected repositories REQUIRES human confirmation
```

Policy evaluation is separate from reachability calculation.

A reachable path can exist while policy says it is forbidden.

## 20. OpenAI / HEIF case-study shape

The motivating case can be represented without claiming facts beyond recorded evidence:

```text
libheif@affected-revision
  --CONTAINS/lineage-->
community-image-runtime@revision

community-image-runtime
  --EXPOSES-->
community-sso-credential

codex-auth-service
  --ACCEPTS_CREDENTIAL-->
community-sso-credential

community-sso-credential
  --CAN_AUTHENTICATE_AS-->
employee-codex-session

employee-codex-session
  --DELEGATES {repo.read, pr.write}-->
github-connector

github-connector
  --HAS_CAPABILITY-->
private-monorepo
```

Then:

```text
affectedness(libheif)
  + compromise model(process code execution)
  + authority reachability
  = evidence-backed potential blast radius
```

Not:

```text
vulnerable libheif == monorepo compromised
```

## 21. Initial implementation phases

### Phase A — core authority substrate

- canonical enums/types;
- append-only authority edge store;
- capability and constraint normalization;
- evidence validation;
- bounded graph traversal;
- path explanation;
- unit tests.

### Phase B — compromise semantics

- compromise-model transition rules;
- credential acceptance;
- audience/scope/binding checks;
- delegation/capability intersection;
- trust-boundary accounting;
- blast-radius query.

### Phase C — joins

- exact identity bridge from lineage/affectedness subjects;
- reliance bridge where useful;
- ProductService projections;
- CLI JSON surface.

### Phase D — adapters

- GitHub connector permissions;
- local process/secret observations;
- selected OAuth/OIDC metadata;
- later cloud/Kubernetes/provider adapters.

### Phase E — product surface

- project security/reachability page;
- path explanation UI;
- "what can this reach?" and "why?" views;
- change/revalidation hooks.

## 22. Definition of done for v1

Authority Graph v1 is complete when all of the following hold:

- authority relations are not represented as lineage edges;
- every edge requires evidence;
- capability and constraint propagation is relation-specific;
- credential audience/scope/binding affect reachability;
- connector delegation preserves least-authority semantics;
- compromise model is explicit;
- traversal is bounded, cycle-safe and reports truncation;
- alternate paths are preserved;
- trust-boundary crossings are explainable;
- authority blast radius distinguishes reachability from exploitation;
- affectedness can join into authority reachability through exact identity;
- CLI/ProductService expose machine-readable results;
- tests cover the motivating parser -> credential -> SSO -> connector -> repository chain;
- no universal security/trust score is introduced.

## 23. Core principle

A system may be locally justified and globally unjustified.

Testamur should make the composed authority path inspectable:

```text
Trust composes.
Justification must compose too.
```
