# Testamur completion specification

Status: canonical closure specification for the Testamur convergence / repository-boundary work.

This document defines what “finish Testamur” means after the W1–W5 convergence. It is deliberately broader than the 0.1 core release gate: it covers namespace retirement, repository boundaries, the GitHub-like product surface, hosted separation, billing/legal shells, deployment shape, and the migration path from the current MathHub transition repository.

The semantic ownership map remains `docs/TESTAMUR_CONVERGENCE.md`. When this document and an older worker/branch note disagree, this document owns completion scope and repository/product boundaries; `TESTAMUR_CONVERGENCE.md` owns the underlying evidence semantics.

## 1. Completion target

Testamur is complete enough to leave the transition repository when all of the following are true:

1. `testamur` is the only active Python/runtime/CLI namespace for the product.
2. Witness is retired as code, package, service, test dependency, workflow identity, and user-facing product name.
3. The open-source core has a coherent local workflow from source observation through explicit reliance and revalidation.
4. The Web product is understandable without knowing internal object names or CLI implementation details.
5. Open-source core/integrations and the private hosted service plane have explicit dependency boundaries.
6. Historical Witness persistence/wire data can be handled without requiring the Witness Python package to exist.
7. Release validation is reproducible locally and in CI, and an unavailable external action/provider does not block unrelated product completion.
8. The current MathHub transition repository can be split without inventing a second Testamur ontology or duplicating semantic engines.

The completion target is not “every future SaaS feature is finished”. Hosted account, billing, organization, collaboration, and scale features may continue after the OSS boundary is publishable, but their interfaces and ownership must already be defined.

## 2. Witness retirement

### 2.1 Hard requirements

The final working tree must not contain active runtime/package trees named:

```text
witness/
witness_service/
```

Testamur production code must not import `witness` or `witness_service`.

`tests/test_testamur_*` must not import retired Witness runtime modules. The release gate must fail if these imports are reintroduced.

Witness-specific workflows, release scripts, examples, evaluations, Web surfaces, and active product documentation are retired rather than kept as a second supported stack. Git history is the archive.

A short retirement marker may remain to explain where historical Witness implementation went, but it must not be importable or executable.

### 2.2 Legacy persistence compatibility

Historical names inside persisted data are different from a live Witness namespace.

The following may temporarily remain when required to open historical local data:

- SQLite table names such as `witness_*`;
- historical wire/protocol identifiers such as `witness-runtime-*`;
- historical IDs embedded in already-created records.

These are **legacy storage/wire inputs**, not current product identity.

New runtime status, newly created protocol envelopes, public Python types, CLI output, docs, and package metadata must use Testamur names.

Do not remove historical schema identifiers by blind string replacement. If the physical SQLite schema is renamed, implement a transactional, versioned migration with tests proving old databases reopen correctly.

The desired end state is:

```text
legacy witness_* data
        ↓ explicit migration/compat reader
canonical Testamur model
        ↓
new writes use Testamur identity
```

## 3. Open-source core boundary

The public Testamur core owns semantic truth about local evidence operations. It includes:

- the `testamur` Python package;
- CLI and local environment lifecycle;
- receipt/evidence storage;
- source/revision identity;
- verification records;
- temporal semantics;
- Policy and Reliance;
- WorkSession and explicit reconciliation;
- lineage / affectedness primitives;
- watch/change/revalidation semantics;
- canonical `TestamurProductService` read boundary;
- local protocol/types needed by integrations;
- migrations required to open historical local data;
- release/namespace gates and core tests.

It does **not** own:

- hosted user accounts or sessions;
- organization/team management;
- hosted authorization and entitlement enforcement;
- subscription billing or payment-provider secrets;
- hosted credits/funding-pool ledger administration;
- hosted production database orchestration;
- email delivery infrastructure;
- SaaS retention administration;
- proprietary ingestion infrastructure;
- deployment secrets or cloud-specific service wiring.

The OSS core may define neutral interfaces or data contracts needed by hosted code, but it must not embed a private service plane inside `testamur/`.

## 4. Integrations / tool boundary

Agent/tool integrations should remain inspectable and open source unless there is a concrete reason otherwise.

The intended public integrations boundary contains, for example:

- Codex integration;
- MCP/tool adapters;
- shell/editor integrations;
- GitHub Action integration where useful;
- host plugins consuming Source Gateway;
- SDK/helper packages that translate host events into Testamur WorkSession/reconciliation operations.

Integrations may capture observations or expose reconciliation choices. They may **not** silently convert “model saw this”, “tool fetched this”, or “source was present in context” into durable reliance.

`EXPOSED_TO_MODEL != RELIED` remains a hard invariant.

The integrations repository depends on Testamur core. Testamur core must not depend on a specific agent host.

## 5. Hosted service-plane boundary

Hosted Testamur is a product/service layer around the OSS semantics, not a fork of them.

The private hosted boundary owns:

- login/session/account/profile flows;
- organizations, teams, invitations, roles and hosted permissions;
- hosted/private projects and source visibility;
- notifications and delivery channels;
- hosted watch scheduling and background workers;
- private upload/retention/erasable metadata controls;
- production database/service orchestration;
- billing, subscriptions, credits and funding-pool administration;
- payment-provider adapters and secrets;
- abuse/rate-limit/operational controls;
- hosted API edge and deployment configuration.

Hosted code must consume Testamur core/ProductService contracts where those semantics apply. It must not create a second Store, Policy engine, Reliance engine, temporal model, affectedness model, or alternative definition of source history.

Files such as hosted billing/catalog/store implementations do not belong in the final OSS core package simply because the Web UI references them.

## 6. Intended repository split

The current `Constanteer/Mathub` repository is a transition workspace, not the intended long-term ownership boundary.

Target shape:

```text
public:  Testamur core
         └─ package / CLI / local runtime / semantic model / migrations

public:  Testamur integrations
         └─ Codex / MCP / editor / shell / host adapters

private: Hosted platform
         ├─ Testamur Web/SaaS
         ├─ Sources
         └─ MathHub product surface
```

Exact repository names may be chosen when the repositories are created; ownership direction is the normative part.

Dependency direction:

```text
integrations ───────► Testamur core ◄────── hosted platform
                                      │
                                      ├─ Sources
                                      └─ MathHub
```

There must be no dependency from Testamur core back into hosted code.

When extracting repositories, prefer history-preserving extraction/clean-forward over copying stale worker branches. The source of truth is the landed convergence/cleanup head, not old `main` snapshots or W1–W5 branch heads.

## 7. Product family and domain shape

A single registered domain is sufficient for the product family.

Canonical product-level navigation should present three understandable products:

```text
Testamur · Sources · MathHub
```

`Sources` is the preferred user-facing name for the previously discussed “Official Sources” surface. `Registry` is an acceptable alternate only if the product evolves toward a registry-first mental model. “Official Sources” should not become a hardcoded ontology term.

Deployment may use either subdomains or top-level product paths, for example:

```text
testamur.example.com
sources.example.com
mathhub.example.com
```

or:

```text
example.com/testamur
example.com/sources
example.com/mathub
```

The root domain should explain the Constanteer/product family rather than forcing all three products into one undifferentiated application shell. Redirects between path and subdomain forms are acceptable.

Product naming/routing must not imply that Sources or MathHub are alternate Testamur semantic engines; they are products that can consume the shared evidence infrastructure.

## 8. Web product completion

The Testamur Web experience should be closer to GitHub’s product grammar than to an internal database viewer.

A user opening the product should quickly understand:

- what projects/sources they are tracking;
- what changed recently;
- what needs attention or revalidation;
- what they are watching;
- their recent activity/work sessions;
- the state of their own projects and monitored dependencies;
- where to create/open a project or connect an integration.

The primary experience is **not** “search a graph” and is not centered on obscure internal commands such as `trace`.

### 8.1 Core Web surfaces

The hosted/product UI should converge toward:

- dashboard/home feed;
- project/source pages;
- activity/history views;
- watch/monitoring state;
- notifications/attention queue;
- status/revalidation surfaces;
- lineage/affectedness explanations where relevant;
- compare/history views;
- user/profile/account surfaces in hosted deployments;
- organization/collaboration surfaces when hosted collaboration is enabled.

A project-like navigation object may be a projection over tracked Sources. Do not add a second durable `Project` ontology merely to make the UI look like GitHub.

### 8.2 UI architecture

The browser and Web API are projections over `TestamurProductService` and explicit hosted service contracts.

Do not put semantic business logic into browser JavaScript just to make a page work. Do not create a Web-only provenance/reliance model.

The GitHub-like visual redesign can be clean-forwarded independently of hosted billing/account implementations when their file boundaries permit it.

## 9. Accounts and collaboration

Accounts are a hosted concern, but the product completion plan should reserve complete flows rather than placeholder buttons.

Hosted account scope includes:

- sign up / sign in / sign out;
- session lifecycle;
- profile/account settings;
- organization/team membership;
- invitations;
- role/permission management;
- private/public visibility policy;
- user activity where appropriate;
- deletion/export/privacy controls required by the deployed service.

The OSS local CLI must remain usable without creating a hosted account.

## 10. Pricing, billing, credits and funding pool

Billing must be provider-agnostic at the product/domain boundary.

Current payment-provider intent is Dodo, but Dodo connectivity, approval, secrets, or production availability must not block unrelated Testamur implementation or release work.

Required hosted billing architecture:

```text
product entitlements / plans / credits
                ↓
provider-neutral billing interface
                ↓
Dodo adapter (or future provider)
```

Until a live provider is available, the product may use feature flags, stub/mock checkout, disabled purchase actions, or an explicit “billing unavailable” state while still implementing:

- plan/catalog model;
- entitlement model;
- subscription state machine;
- credits/funding-pool ledger semantics;
- billing UI states;
- invoices/receipts metadata model where applicable;
- provider adapter boundary;
- failure/cancellation/refund state handling;
- tests and documentation.

Payment-provider absence is not a reason to mix billing logic into the OSS core.

## 11. Pricing and legal product pages

Before public paid launch, the hosted site should have coherent non-placeholder versions of:

- Pricing;
- Terms of Service;
- Privacy Policy;
- Refund Policy;
- billing/subscription disclosure as needed;
- contact/support path;
- any required account deletion/data handling explanation.

These pages are hosted-product obligations, not Testamur semantic-core modules.

Do not block the OSS release on payment-provider approval, but do not present paid checkout as live until the operational/legal path actually exists.

## 12. Deployment and packaging

The hosted service does not require a custom CPython build.

Default deployment should use an ordinary supported Python runtime (for example Python 3.12) in a reproducible environment/container. `uv`, standard virtual environments, wheels, or normal container packaging are sufficient.

The public CLI should initially optimize for boring, reproducible installation:

```text
wheel / sdist
pipx or uv tool install
```

Standalone macOS/Linux/Windows binaries may be added later if distribution friction justifies them. They should package Testamur, not require maintaining a private CPython fork.

Open-source CLI packaging and hosted Web deployment are separate release artifacts.

## 13. Release and test closure

### 13.1 Canonical local validation

The repository-local release gate is authoritative for the exact checkout on which it executes:

```bash
bash scripts/testamur_local_gate.sh release
```

A smoke mode may be used during development; release mode is required before declaring an exact head ready.

CI should run the same semantic gate rather than defining a second test truth.

### 13.2 Structural namespace invariants

Release validation must fail when:

- `witness/` or `witness_service/` reappears as active runtime code;
- packaged modules include Witness namespaces;
- Testamur production code imports Witness;
- Testamur tests rely on retired Witness runtime modules;
- the CLI/package entrypoint resolves to a legacy namespace.

Legacy persistence identifiers are permitted only where explicitly classified as migration/storage compatibility.

### 13.3 CI infrastructure

A checkout/network/runner/bootstrap failure is an infrastructure failure, not evidence that Testamur semantics failed.

Conversely, an unexecuted job is not green.

Self-hosted CI must avoid assumptions specific to GitHub-hosted toolcache paths. The workflow should use an available Python toolchain, create an isolated environment, install its build/test backend explicitly, and then invoke the repository-local gate.

Repository-wide MathHub/Lean checks should not continuously starve Testamur release validation when Testamur-only files change.

## 14. Release invariants retained from convergence

The following remain non-negotiable:

- recorded != verified;
- fetched != relied;
- exposed-to-model != relied;
- changed != invalid;
- stale != false;
- lineage != affectedness verdict;
- upload != publication rights;
- hosted != trusted;
- paid != verified;
- `KNOWN_AT != AVAILABLE_BY != EFFECTIVE_AT`.

A complete local reliance loop should remain intelligible as:

```text
SourceRevision
  → WorkSession
  → explicit reconciliation
  → Policy
  → Reliance
  → Watch/change
  → impact / affectedness
  → revalidation
```

For a WorkSession to be considered fully reconciled when durable reliance is exported, required durable follow-up state (for example a watch candidate when mandated by the model) must also be materialized; tests should exercise the entire invariant rather than force a partial state to look reconciled.

## 15. Migration / closure sequence

Preferred order from the current transition repository:

1. converge #172 against the latest semantic base and get the exact combined head through release validation;
2. finish Testamur-test namespace cleanup and prevent Witness resurrection in the gate;
3. retain only explicit legacy storage/wire compatibility;
4. clean-forward the validated GitHub-like Testamur UI without pulling hosted service-plane code into OSS core;
5. collapse/close superseded convergence/UI worker PRs once their useful deltas are represented;
6. land the cleanup/convergence line into the canonical branch;
7. create/extract the public Testamur core repository from that canonical state;
8. extract public integrations/tool adapters;
9. move hosted Web/account/billing/service-plane code into the private hosted repository;
10. restore MathHub as an independently understandable product/repository rather than a container for Testamur internals;
11. choose and apply the public open-source license when the public repository boundary is explicit;
12. deploy the product family under the single-domain routing scheme.

Do not create new repositories from the stale pre-convergence `main` tree.

## 16. Definition of done

### 16.1 OSS/core done

The OSS core is ready to extract/publish when:

- [ ] one canonical Testamur namespace/package exists;
- [ ] Witness runtime/service trees are absent;
- [ ] Testamur code/tests have no retired Witness runtime imports;
- [ ] legacy persisted data compatibility is explicit and tested;
- [ ] CLI install/run works from a fresh installation;
- [ ] ProductService/Web semantic boundary tests pass;
- [ ] release gate passes on the exact candidate head;
- [ ] repository split destination is clear;
- [ ] an open-source license has been selected before public release.

### 16.2 Hosted product foundation done

The hosted foundation is ready for product iteration when:

- [ ] GitHub-like dashboard/project/activity/watch/attention flows are coherent;
- [ ] account/session/profile/permission boundaries are implemented or explicitly feature-gated;
- [ ] hosted code consumes rather than duplicates Testamur semantics;
- [ ] billing is provider-agnostic and a Dodo adapter boundary exists;
- [ ] unavailable payment connectivity produces an explicit disabled/stub state rather than blocking the application;
- [ ] credits/funding-pool semantics have a defined ledger/state model;
- [ ] Pricing, Terms, Privacy and Refund pages are present before paid public launch;
- [ ] deployment does not depend on a custom CPython fork;
- [ ] Testamur / Sources / MathHub product routing is understandable under the single registered domain.

### 16.3 Explicit non-goals for this closure

The following are not required to declare the OSS Testamur core complete:

- a live Dodo merchant connection;
- every GitHub-equivalent social feature;
- custom CPython;
- standalone native binaries;
- enterprise-scale hosted infrastructure;
- a second semantic implementation for Web/hosted use;
- preserving an importable Witness compatibility package forever.
