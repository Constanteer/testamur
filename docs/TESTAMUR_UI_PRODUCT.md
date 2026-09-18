# Testamur Product UI — Early Launch Design

> **Status:** product/UI direction for the first public Testamur surface.
>
> This document is intentionally separate from `WITNESS_UI_V2.md`. `WITNESS_UI_V2.md` defines browser truth/provenance behavior and verifier contracts. This document defines the **human product surface**: information architecture, page hierarchy, visual interaction model, and the smallest coherent UI that can launch early.

---

## 1. Product UI thesis

Testamur should not look like a generic knowledge-base app, a dashboard-only monitoring SaaS, or a graph toy.

The UI should combine three familiar interaction models:

```text
GitHub-like object pages
    → what this object is, how it changed, what relates to it

Cloudflare-like operations pages
    → what I am watching, current state, failures, rules, quotas

Wayback-like historical navigation
    → what existed at a particular time and how revisions evolved
```

The key separation is:

```text
OBJECT SURFACE          OPERATIONS SURFACE
public / canonical      user / workspace specific
GitHub-like             Cloudflare-like

"What is this?"         "What am I doing with it?"
"How did it change?"    "Is it healthy?"
"What depends on it?"   "What changed recently?"
"What is its history?"  "What am I watching?"
```

Do not merge these into one giant dashboard.

A public Source or Record must remain understandable without an account.

---

## 2. Early-launch principle

Do not launch the UI as a universal epistemic operating system.

Launch one narrow but real vertical slice:

```text
Source
→ Snapshot / Revision
→ History
→ Mechanical Compare
→ Record
→ Relation
→ Watch / Alert
```

This slice already demonstrates the long-term architecture:

```text
persistent identity
+ immutable revisions
+ provenance
+ typed relations
+ temporal history
```

The first release does **not** require:

```text
full Lab workflows
Business control plane
Enterprise deployment UI
universal ontology editor
AI semantic diff as authority
complex agent orchestration UI
large social layer
full Internet crawling
```

MathHub can remain a structured domain showcase on top of the same design language.

---

## 3. Core design laws

### 3.1 The object is primary

Every important public object should have a canonical page and stable URL.

Examples:

```text
/source/<source-id>
/snapshot/<snapshot-id>
/record/<record-id>
/compare/<left>...<right>
/collection/<collection-id>
```

The user should be able to send a Testamur URL as an ordinary reference without explaining a workspace or dashboard context.

### 3.2 History is not premium UI

Canonical public history is a first-class part of the public object page.

Do not visually imply that older public revisions disappear behind Pro.

### 3.3 Mechanical facts first

The default UI shows inspectable facts:

```text
revision identity
capture time
source locator
hash / digest
exact diff
recorded relation
who/what created a relation
which revision is pinned
```

Model-generated interpretation, if present in later releases, is visually secondary and explicitly non-authoritative.

### 3.4 Never collapse epistemic distinctions into one score

Avoid generic UI such as:

```text
Trust score: 92%
Confidence: High
AI says this is true
```

Prefer explicit states and evidence/provenance surfaces.

### 3.5 Public and private use the same conceptual objects

A private Source should not become a different species of object. Privacy changes visibility, access policy, quota accounting, and collaboration — not its identity semantics.

### 3.6 Graphs are navigation, not decoration

The graph must answer a question. Default to local neighborhood / bounded paths, not a full-screen hairball.

---

## 4. Global shell

### 4.1 Top bar

The persistent top bar should be sparse and GitHub-like.

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Testamur   [ Search or jump to…                              ]  +  ◉ │
└──────────────────────────────────────────────────────────────────────┘
```

Recommended contents:

```text
brand / home
universal search / command bar
create button
alerts inbox
account / workspace switcher
```

Search should eventually support structured filters but the first release can expose plain search with filter chips.

Example future syntax:

```text
type:record relation:contradicts domain:math
source:example.com changed:30d
```

### 4.2 User/workspace sidebar

Use a Cloudflare-like left navigation only inside the signed-in operations surface.

```text
Overview
Watch
Alerts
Sources
Records
Collections
Graph
Activity
API
Settings
```

Later organization tiers may add:

```text
Members
Policies
Audit
Integrations
Runners
Retention
Security
```

Do not show enterprise-only navigation to ordinary users by default.

### 4.3 Public object pages

Public object pages should not depend on the operations sidebar.

They use a simpler object header and horizontal local navigation.

---

## 5. Landing / unauthenticated home

The first public page should explain the product through an action rather than a manifesto.

```text
                         Testamur

                The history behind what we know.

┌────────────────────────────────────────────────────────────┐
│ https://example.com/...                                    │
└────────────────────────────────────────────────────────────┘
                                             [ Track source ]

Explore
──────────────────────────────────────────────────────────────
OpenAI Model Spec
173 snapshots · last changed 4h ago

FDA Guidance
32 snapshots · 14 records reference revisions

Nat.add_comm
Lean verified · 28 dependents
```

Primary first-use loop:

```text
paste URL
→ preview source
→ start tracking / inspect existing source
→ see timeline
→ compare revisions
→ create or inspect a Record tied to an exact revision
```

The homepage should not lead with:

```text
Create workspace
Configure ontology
Connect integrations
Choose verification policy
```

Those are later actions.

---

## 6. Signed-in overview

The signed-in home is operational, not a second marketing page.

```text
Overview
──────────────────────────────────────────────────────────────
14 changes since yesterday
3 source checks failed
2 records affected
1 source unavailable

Your watch
──────────────────────────────────────────────────────────────
OpenAI Model Spec             Changed       12 min ago
Anthropic system cards        Healthy        1 h ago
FDA Guidance                  Changed        3 h ago
NIST AI RMF                   Unavailable    5 h ago

Pinned collections
──────────────────────────────────────────────────────────────
AI policy
Semiconductor supply chain
Math verification
```

The overview should prioritize:

```text
changes
failures
attention required
recently active watched objects
```

Avoid vanity metrics unless they are operationally useful.

---

## 7. Source page

The Source page is the first major launch page.

### 7.1 Header

```text
OpenAI / Model Spec                                      Public
model-spec.openai.com

● Healthy

[ Overview ] [ History ] [ Compare ] [ Records ] [ Relations ]

[ Watch ] [ Add record ]
```

The header should answer immediately:

```text
what source is this?
is it currently observable?
when was it last checked?
when did it last change?
how long have we observed it?
```

### 7.2 Overview body

```text
Current revision
──────────────────────────────────────────────────────────────
Observed              2026-09-13 14:52 UTC
Revision               srcrev_...
Digest                 sha256:...
Locator                https://...
First observed         2025-02-11
Last changed           2026-09-12
Snapshots              173
Records linked         24

Recent history
──────────────────────────────────────────────────────────────
Sep 13   ● observed — no content change
Sep 12   ● content changed          +17 -9
Sep 09   ● content changed           +3 -1
Sep 02   ● metadata changed
```

### 7.3 Right rail

Use a compact GitHub-like right rail for metadata, not a dense control panel.

Possible blocks:

```text
About
Canonical ID
Visibility
First observed
Current locator
Content type
License / rights state where known
Watchers
Related collections
```

Operational settings belong in Watch/Edit, not in this rail.

---

## 8. Snapshot / revision page

A Snapshot is an immutable historical observation.

```text
Source: OpenAI / Model Spec
Revision: src_rev_0194
Observed: 2026-09-12 08:14 UTC

[ View content ] [ Compare ] [ Provenance ]
```

Show:

```text
exact capture/observation timestamp
content digest
HTTP / retrieval metadata where available
raw or rendered content according to rights
previous / next revision
records pinned to this revision
```

Never silently redirect an old revision to the latest revision.

If a newer revision exists, display a neutral notice:

```text
A newer revision has been observed.
[ View current ]
```

---

## 9. History page

History should feel closer to GitHub commits + Wayback navigation than to a generic activity feed.

```text
History
──────────────────────────────────────────────────────────────
[ 2026 ] [ 2025 ] [ 2024 ] [ All ]

Sep 13   ● observed — unchanged
         │
Sep 12   ● content changed
         │  +17 -9
         │  3 sections changed
         │
Sep 09   ● content changed
         │  +3 -1
         │
Sep 02   ● metadata changed
```

Later, add a compact year/month navigator:

```text
2026
│
● Sep
│
● Aug
│
● Jul
│
2025
│
● Dec
```

### 9.1 Time navigation

The long-term surface should support an `As of` control:

```text
As of: [ 2025-06-01  ▾ ]
```

This must reconstruct the state from recorded temporal data, not ask a model to imagine what was known at that time.

Long-term direction:

```text
2022 ───── 2023 ───── 2024 ───── 2025 ───── 2026 ●
                         ↑
                    inspect state here
```

This control can later apply not only to a Source but to a Record neighborhood / graph view.

---

## 10. Compare page

Compare is mechanical first.

```text
Compare revisions
src_rev_0193  →  src_rev_0194

[ Text ] [ Structure ] [ Metadata ] [ Headers ] [ Raw ]
```

Example:

```diff
- The system may operate autonomously.
+ The system may operate autonomously under supervision.
```

Useful deterministic side information:

```text
+17 additions
-9 deletions
3 headings changed
1 link added
2 links removed
```

If DOM-aware or structured diff is available, it must remain reproducible and inspectable.

### 10.1 Semantic interpretation

Do not make model semantic diff part of the canonical comparison result.

If introduced later:

```text
Derived interpretation
⚠ Non-authoritative model-generated view
Model: ...
Generated from: rev_0193 → rev_0194
```

The user must always be able to inspect the underlying mechanical diff.

---

## 11. Record page

A Record gives a persistent identity to something worth referring to across time.

Early Record types may include:

```text
claim / assertion
requirement
observation
specification statement
mathematical claim
artifact-level result
```

The UI should not force all Record types into identical epistemology.

### 11.1 Header

```text
record/tst_8f3a...

"The system retains logs for 30 days."

Public · Current revision r7

[ Overview ] [ History ] [ Basis ] [ Relations ] [ Challenges ]

[ Watch ] [ Cite ] [ Add relation ]
```

### 11.2 Main body

```text
Statement
──────────────────────────────────────────────────────────────
The system retains logs for 30 days.

Based on
──────────────────────────────────────────────────────────────
example.com/policy
revision src_rev_0194
observed 2026-09-13
§4.2 / exact region if available

Relations
──────────────────────────────────────────────────────────────
supersedes      record:tst_18...
used by         project:foo
contradicted by record:tst_a8...
```

### 11.3 Basis

`Basis` is broader than mathematical axioms.

Possible typed basis entries:

```text
Math
- axiom
- definition
- assumption
- formal system

Science
- observation
- measurement
- dataset
- protocol
- model

Engineering
- requirement
- constraint
- standard
- specification
- test result

History / archival work
- primary source
- testimony
- artifact
- archival record
```

The shared UI concept is:

> What inputs does this Record rely on without expanding them further in this local view?

Do not imply all basis types carry the same epistemic force.

---

## 12. Create Record from Source

One of the most important launch interactions is creating a Record from an exact source revision.

Expected interaction:

```text
1. open source revision
2. select text / region
3. click "Create record"
4. enter normalized statement / title
5. retain exact source revision + region reference
6. publish or keep private
```

Creation sheet:

```text
Create record
──────────────────────────────────────────────────────────────
Statement
[ The system retains logs for 30 days.                    ]

Source revision
example.com/policy @ src_rev_0194

Exact region
§4.2 / selection anchor

Visibility
(●) Public
( ) Private

[ Create record ]
```

The UI must make it obvious that:

```text
Record statement != source bytes
```

A Record can be a normalized assertion derived from a source, while the source revision remains independently inspectable.

---

## 13. Relations

Relations are first-class objects, not merely graph lines.

Initial relation vocabulary should remain small:

```text
supports
depends-on
contradicts
supersedes
cites
```

Additional domain-specific types can come later.

A relation should be inspectable:

```text
A --supports--> B

Relation details
──────────────────────────────────────────────────────────────
Type                supports
From                record:A@r3
To                  record:B@r7
Created by          ...
Recorded at         ...
Evidence / basis    optional exact references
Status              active / superseded / challenged
```

Edges must retain provenance.

Do not render relation creation as an invisible side effect of AI extraction.

---

## 14. Graph page

The graph is a structured navigation mode.

Default local view:

```text
                      [ Basis A ]
                           │
                           ▼
[ Record X ] ───────→ [ Record Y ] ───────→ [ Record Z ]
       ▲                  │
       │                  ▼
 [ Source R ]       [ Contradiction C ]
```

Recommended controls:

```text
relation type filters
incoming / outgoing toggle
depth 1 / 2 / 3
as-of time
show sources
show records
show challenges
```

Selecting a node opens a right-side inspector rather than navigating immediately.

Inspector:

```text
Record
────────────────────────────────────
Title
Current revision
First observed / created
Basis count
Incoming relations
Outgoing relations
Challenges

[ Open full page ]
```

The graph should default to a bounded neighborhood. Global world views can use level-of-detail clustering similar to the existing MathHub graph direction.

---

## 15. Watch page

Watch is the Cloudflare-like operational surface.

```text
Watch
──────────────────────────────────────────────────────────────
Tracked sources          128
Healthy                  121
Changed today             14
Check failures              3

Source                         Last check        State
──────────────────────────────────────────────────────────────
OpenAI Model Spec             2 min ago         ● Changed
FDA Guidance                  8 min ago         ● Healthy
Example supplier spec        11 min ago         ● Failed
```

### 15.1 Source watch settings

```text
Monitoring
──────────────────────────────────────────────────────────────
State             Active
Check cadence      6 hours
Last success       2 min ago
Last change        Sep 12
Consecutive errors 0

Alerts
Email              on
Webhook            off

[ Pause ] [ Check now ] [ Edit ]
```

Free users should have a useful baseline Watch and alert experience.

Paid tiers increase scale/frequency/private capacity rather than unlocking the existence of Watch.

---

## 16. Alerts

Alerts are available in Free at a basic level.

Inbox shape:

```text
Alerts
──────────────────────────────────────────────────────────────
● Source changed
  OpenAI Model Spec
  12 min ago

● Check failed
  example.com/spec
  1 h ago

● Upstream revision changed
  Record tst_8f3a depends on changed source revision
  4 h ago
```

Keep early alert rules deterministic.

Examples:

```text
source changed
source unavailable
new revision observed
record relationship added
upstream pinned source has newer revision
```

Avoid launching with broad AI-authored rules such as "notify me when this claim becomes weaker".

---

## 17. Search

Search results should mix object types but clearly label them.

```text
Search: "retention"

RECORD
The system retains logs for 30 days
record/tst_8f3a

SOURCE
Example Product Data Policy
example.com/policy

MATH CLAIM
Nat.add_comm
Lean verified
```

Filters:

```text
All
Records
Sources
Snapshots
Collections
Math
```

Later structured filters may include:

```text
changed:7d
relation:contradicts
visibility:public
source-domain:example.com
```

---

## 18. Collections

Collections are lightweight curated groupings, not separate ontologies.

Examples:

```text
AI policy
Semiconductor supply chain
Climate datasets
Math verification
```

Collection page:

```text
AI policy
──────────────────────────────────────────────────────────────
24 sources
61 records
Last activity 12 min ago

[ Overview ] [ Sources ] [ Records ] [ Activity ] [ Graph ]
```

Collections help users create a coherent watch surface without forcing everything into a formal Project object on day one.

---

## 19. MathHub domain surface

MathHub should use the same shell but retain domain-specific tabs and semantics.

Example:

```text
Nat.add_comm
Claim · Lean verified

[ Overview ] [ Proofs ] [ Dependencies ] [ Used by ] [ History ]
```

The shared visual grammar is:

```text
stable object identity
revision
history
relations
basis / dependencies
verification state
```

But Testamur must not pretend a Lean proof, empirical dataset, and company web page have identical verification semantics.

MathHub is useful as an early showcase because it proves that Testamur is not merely a web-change tracker.

---

## 20. Pricing / entitlement UI

The early public pricing page can remain simple even if the long-term service model includes Free / Pro / Lab / Business / Enterprise.

### Early launch presentation

```text
FREE
For everyone

- full public history
- public records
- custom sources
- baseline watch
- basic alerts
- small private quota
- basic API

PRO
For people tracking more

- more watches
- higher check frequency
- larger private quotas
- higher API limits
- more alert endpoints / automation
```

Then:

```text
Labs & organizations
Join early access
```

Do not expose empty enterprise navigation just to make the product look larger.

### Quota UI

Prefer transparent GitHub-like quota messaging:

```text
Private sources
3 / 5 used

Tracked sources
128 / 1,000
```

Do not blur public history behind upgrade overlays.

---

## 21. Visual style

The product should feel technical, durable, and inspectable rather than futuristic for its own sake.

Recommended character:

```text
high information density, but not terminal-like
neutral surfaces
clear borders and grouping
compact typography
monospace only for IDs / hashes / code / raw data
status color used sparingly
strong focus on chronology and identity
```

Avoid:

```text
giant gradient hero sections inside the app
floating-glass dashboards
AI sparkle iconography everywhere
unexplained confidence meters
full-screen force graphs as default navigation
excessive cards for every line of metadata
```

A useful aesthetic reference is the seriousness of developer/infrastructure tools rather than consumer AI chat products.

---

## 22. Status vocabulary

Use precise status labels and avoid overloading them.

Examples:

```text
Source monitoring
Healthy
Changed
Unavailable
Check failed
Paused

Record lifecycle
Current
Superseded
Withdrawn
Challenged

Verification / assurance
Verified by <mechanism>
Not verified
Unknown
Stale
```

Do not allow UI color alone to imply universal truth.

`STALE` is not `FALSE`.
`UNAVAILABLE` is not `RETRACTED`.
`SUPERSEDED` is not necessarily `WRONG`.

---

## 23. Mobile behavior

The mobile product does not need feature parity for graph manipulation in the first release.

Prioritize:

```text
search
source overview
history
compare
record reading
alerts
watch status
```

Graph can become a read-only / simplified local-neighborhood view initially.

Object metadata rails should collapse beneath the main content.

---

## 24. Early launch route map

A practical first route set:

```text
/
/login
/search

/source/:id
/source/:id/history
/source/:id/compare/:left/:right
/snapshot/:id

/record/:id
/record/:id/history
/record/:id/relations

/watch
/alerts
/collections
/collection/:id
/settings
```

Later:

```text
/graph
/workspaces/:id
/orgs/:id
/orgs/:id/members
/orgs/:id/policies
/orgs/:id/audit
/as-of/:timestamp/...
```

---

## 25. MVP acceptance criteria

The first public UI is coherent if a new user can complete this sequence without documentation:

```text
1. paste a URL
2. understand whether Testamur already tracks it
3. inspect its current revision
4. view historical revisions
5. compare two revisions mechanically
6. create or open a Record tied to one exact revision
7. inspect at least one relation from that Record
8. watch the Source
9. receive a basic change alert
10. share a canonical public Source or Record URL
```

The product is not ready if the primary demo requires explaining internal terms before the user can see why it is useful.

---

## 26. Release sequence

### Alpha

```text
Source
Snapshot
History
Compare
Watch
Alert
Record
Relation
Search
```

### Alpha + MathHub showcase

```text
formal claims
proofs
proof dependencies
Lean verification
MathHub graph
```

### Beta

```text
collections
private sources / records
better alert routing
cross-record impact views
public API
imports
basic graph exploration
```

### Lab / Business

```text
shared workspaces
permissions
private graph
review / approval
publication flows
connectors
organization audit
```

### Long-term temporal graph

```text
"View world as of <time>"

source state
record state
relations
basis
challenges
known dependents
available evidence / provenance
```

The long-term "Internet time machine" experience should emerge from the temporal data model rather than from a separate archive feature.

---

## 27. Product sentence for the UI team

A useful implementation test is:

> **GitHub tells you what code is and how it changed. Cloudflare tells you what you operate and whether it is healthy. Testamur should tell you what an inspectable record is, what exact sources/revisions it rests on, how that structure changed over time, and what currently depends on it.**

The first UI does not need to show the entire future of Testamur. It must make that idea obvious in one ordinary user session.
