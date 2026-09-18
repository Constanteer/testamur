# Testamur Temporal Model

> **Status:** canonical temporal-semantics specification for the converged Testamur core.
>
> This document defines how immutable revision/history machinery reconstructs not only **what the database looked like**, but also **what was known, publicly available, or effective at a given time**.
>
> Runtime ownership is now Testamur-owned: `temporal_model.py`, `temporal_store.py`, and `temporal_query.py` implement the canonical temporal layer described here. Historical Witness documents may explain provenance of the design, but they are no longer active owners or required runtime dependencies.

---

## 1. Why a temporal model is required

Testamur already preserves immutable object revisions, source revisions, relation lifecycles, project-state snapshots, and historical reconstruction.

That is necessary but not sufficient for the long-term product.

A single timestamp cannot answer all of these questions correctly:

```text
What did Testamur know on 2025-06-01?

What information was publicly available by 2025-06-01?

What rule, claim, specification, or relation was actually effective on 2025-06-01?

When did Testamur first discover that an older fact had already been true?

What did a particular project believe at the time, before a later correction arrived?
```

These are different temporal questions and may produce different answers.

The key design law is:

> **Recorded time, publication time, and effective time must never be silently collapsed into one timeline.**

---

## 2. The three primary time dimensions

Testamur should model at least three independent notions of time.

### 2.1 Transaction / observation time

This is when a Testamur node/perspective actually recorded an observation or state transition.

Examples:

```text
retrieved_at
recorded_at
created_at
captured_at
attested_at
relation_recorded_at
state_revision.created_at
```

This time is authoritative only for the statement:

> Testamur had this durable record by this time.

It must not be interpreted as the time when the external fact became true.

Suggested normalized name:

```text
recorded_at
```

Where an existing owner already exposes a more precise field such as `retrieved_at`, the normalized temporal layer should project it into recorded/observation time rather than duplicate storage.

---

### 2.2 Publication / availability time

This is when a source, artifact, statement, release, paper, regulation, or other externally observable object claims to have become publicly available.

Examples:

```text
paper publication date
webpage publication metadata
Git release time
regulatory bulletin release date
press release publication time
repository commit time
archival document issue date
```

Suggested normalized name:

```text
published_at
```

This field is provenance-bearing and may itself have an evidence class.

For example:

```text
published_at = 2024-03-14
publication_time_basis = source_metadata
```

or:

```text
published_at = 2024-03-14
publication_time_basis = archive_observation
```

Publication time may be:

```text
observed
externally_declared
derived
unknown
```

Testamur must not pretend a declared date is mechanically observed when it is not.

---

### 2.3 Valid / effective time

This is when a Record, relation, policy, specification, legal rule, model assumption, organizational decision, or other temporal object is asserted to apply in the represented world or domain.

Suggested interval:

```text
valid_from
valid_until
```

Examples:

```text
policy published:      2025-01-10
policy effective:      2025-02-01
Testamur first fetch:  2025-03-20
```

These are three distinct facts.

`valid_until = null` means open-ended/unknown end, not necessarily permanent.

Effective time may also be uncertain or externally declared. Therefore the temporal layer should permit provenance for validity claims rather than treating every interval as an unquestionable physical fact.

---

## 3. Optional domain-specific event time

Some domains need the time when an underlying event occurred, which is neither publication nor validity.

Examples:

```text
experiment performed_at
incident occurred_at
measurement sampled_at
interview conducted_at
contract signed_at
satellite observation time
```

This should not become a mandatory fourth global column on every object.

Instead, domain schemas may expose typed event-time fields which the temporal projection can index as:

```text
event_time
```

The invariant is that domain event time must not be silently substituted for recorded, published, or valid time.

---

## 4. Core temporal query modes

The product should expose distinct query semantics.

### 4.1 `KNOWN_AT(T)`

Definition:

> Return only durable state that the queried Testamur/Witness node had actually recorded by time `T`.

This is the strict historical epistemic view.

A late-imported 2023 paper first captured in 2028 does **not** appear in `KNOWN_AT(2024)`.

Conceptually:

```text
KNOWN_AT(T)
= records whose recorded_at <= T
  interpreted using only historical state available by T
```

This is the correct mode for questions such as:

```text
What did this project know at the time?
What evidence had been captured before this decision?
Why did the system believe this in 2025?
Could this later correction have influenced the original decision?
```

`KNOWN_AT` must never leak later observations backward.

---

### 4.2 `AVAILABLE_BY(T)`

Definition:

> Return material that current provenance indicates was publicly available by time `T`, even if Testamur learned about it later.

Example:

```text
Paper publication:      2023-04-01
Testamur first capture: 2028-01-20
```

Then:

```text
KNOWN_AT(2024)      -> excludes paper
AVAILABLE_BY(2024)  -> may include paper
```

provided the publication/availability time is supported by explicit provenance.

This query answers retrospective historical questions such as:

```text
What could a diligent researcher have found by 2024?
What material was publicly available before this event?
What was the public record at that time, according to evidence we have now?
```

It must visually indicate that some items were **recognized retrospectively**.

Suggested UI badge:

```text
Available then · discovered by Testamur later
```

---

### 4.3 `EFFECTIVE_AT(T)`

Definition:

> Return Records and Relations whose represented validity interval includes `T`, using the selected evidence/revision context.

Conceptually:

```text
valid_from <= T
AND
(valid_until is null OR T < valid_until)
```

This answers questions such as:

```text
Which specification was in force on this date?
Which regulation applied when the event occurred?
Which model assumption was active in this project state?
Which organizational policy governed this decision?
```

`EFFECTIVE_AT` is not equivalent to truth.

A historically effective policy can later be discovered to have been invalidly issued; an old scientific model can have been the working model in force for a project without being physically correct.

---

## 5. Query composition

The three query modes should compose rather than compete.

Examples:

```text
KNOWN_AT(2025-06-01)
AND EFFECTIVE_AT(2025-05-15)
```

means:

> Using only what Testamur knew by June 1, reconstruct what it believed was effective on May 15.

Another example:

```text
AVAILABLE_BY(2024-12-31)
AND EFFECTIVE_AT(2024-12-31)
```

means:

> According to present provenance, show material that was both publicly available and effective by the end of 2024.

The UI and API must make the selected temporal mode explicit.

No generic `as_of=T` parameter should silently choose among these meanings.

---

## 6. Historical state versus historical truth claims

Testamur must distinguish:

```text
historical database state
```

from:

```text
claims about the historical world
```

`WITNESS_REVISION_DAG.md` already provides exact reconstruction of historical project state.

This document adds a second layer:

```text
project state revision
        ↓
exact historical graph
        ↓
temporal interpretation
        ↓
KNOWN_AT / AVAILABLE_BY / EFFECTIVE_AT views
```

The first layer is mechanically reconstructible.

The second depends on recorded temporal fields and their provenance.

Do not retroactively mutate an old state snapshot merely because new evidence changes our present interpretation of the past.

---

## 7. Late-arriving historical evidence

Late-arriving evidence is a first-class case, not an anomaly.

Example:

```text
2024-01-01   event E occurs
2024-01-03   source S is published
2028-06-01   Testamur first captures S
```

The new 2028 observation may establish that S was already available in 2024.

Correct behavior:

```text
KNOWN_AT(2024-12-31)
  -> excludes S

AVAILABLE_BY(2024-12-31)
  -> includes S if publication provenance supports it

KNOWN_AT(2028-06-02)
  -> includes S plus the fact that it claims/establishes 2024 publication
```

The 2028 import must not rewrite 2024 transaction history.

Suggested relation/event vocabulary:

```text
RETROSPECTIVE_DISCOVERY
LATE_OBSERVATION
HISTORICAL_AVAILABILITY_ESTABLISHED
```

These should be durable events, not silent index updates.

---

## 8. Retrospective correction

A later source may show that an earlier Record was wrong about the past.

Example:

```text
2025 project state:
Record A: system entered service in 2019

2027 newly discovered archive:
Record B: system entered service in 2018
```

The correct model is not:

```text
rewrite 2025 history so A never existed
```

It is:

```text
2025 historical project state still contains A
2027 current state records challenge/correction B
current retrospective view of 2019 may now differ
```

This yields two valid questions:

```text
What did the project believe in 2025?
```

and:

```text
What do we now believe happened in 2018-2019?
```

Both must remain answerable.

---

## 9. Temporal relations

Relations need time semantics independent of edge recording time.

A relation should be able to carry or resolve:

```text
recorded_at
valid_from
valid_until
```

Example:

```text
Supplier A --approved_supplier_for--> Product X

recorded_at = 2026-03-10
valid_from  = 2026-02-01
valid_until = 2026-08-31
```

The relation was recorded in March but represented as effective beginning in February.

Retraction is not automatically identical to `valid_until`.

For example:

```text
edge recorded       March 10
edge valid until    August 31
edge retracted      September 12
```

Retraction means the graph no longer treats the relation as active in the current asserted structure. `valid_until` records the represented temporal interval.

Both may exist and answer different questions.

---

## 10. Temporal uncertainty and provenance

Not all dates are exact.

The model should permit temporal assertions to carry:

```text
precision
basis
source_ref
confidence_class / evidence_class where domain-defined
```

Possible precision:

```text
instant
day
month
year
interval
before
after
circa
unknown
```

Example:

```text
published_at = 1943
precision = year
basis = archival_catalog
```

or:

```text
valid_from = before(1912-06-01)
basis = later retrospective source
```

Testamur should not coerce fuzzy historical dates into false precision merely for indexing convenience.

A query engine may internally normalize intervals for search, but the original assertion and precision must remain inspectable.

---

## 11. Global `as-of` projection

The long-term public product needs a global temporal graph view without requiring one giant immutable snapshot of the entire network.

The recommended model is a **consistent temporal projection**, not a monolithic global-state commit.

For transaction-time reconstruction:

```text
GLOBAL_KNOWN_AT(T)
```

selects, for each visible public/network object and relation, only state that was durably present by `T` under the selected network perspective.

Conceptually:

```text
for each object:
  choose latest visible revision with recorded_at <= T

for each relation:
  include if relation was recorded by T
  and had not been retracted by T

for each source observation:
  include only receipts/revisions observed by T
```

This produces a mechanically grounded global historical projection without fabricating a single canonical world snapshot.

---

## 12. Network perspective must be explicit

A distributed/federated Testamur network cannot assume one omniscient global observation time.

Different nodes may learn the same thing at different times.

Therefore global historical queries need a perspective/scope.

Examples:

```text
node:testamur-cloud
workspace:org-x
project:project-y
peer-set:public-network-v1
```

A future API may expose:

```text
KNOWN_AT(T, perspective=P)
```

The phrase “what Testamur knew” is incomplete unless the relevant hosted/network perspective is defined.

Testamur Cloud may expose its own hosted-network perspective as the default public product view, while local/federated nodes retain their own authoritative local histories.

---

## 13. Cross-project temporal consistency

Project state DAGs remain project-local and should not be forced into one global DAG.

Cross-project historical queries should instead resolve each project/object under a shared temporal cut.

Example:

```text
cut = recorded_at <= 2026-01-01T00:00:00Z
```

Then:

```text
Project A -> latest state visible before cut
Project B -> latest state visible before cut
Project C -> latest state visible before cut
```

Cross-project relations are then filtered under the same cut.

This produces a consistent transaction-time projection without inventing cross-project parent edges.

If distributed replication means visibility was not globally atomic, the query result should expose that the cut is a **best available consistent projection**, not a claim of simultaneous physical observation everywhere.

---

## 14. Source time semantics

Source objects should project the following times where available:

```text
source first observed
source revision retrieved_at
source declared published_at
source last observed unchanged
source revision superseded/changed observation time
```

The Source page may therefore show:

```text
Published               2025-02-11
First observed by us    2025-02-14
Last checked            2026-09-13
Last changed            2026-09-12
```

These labels must not collapse into one generic “date”.

---

## 15. Record time semantics

A Record revision should support temporal projection without forcing every domain to use validity intervals.

Possible fields/projections:

```text
recorded_at
asserted_published_at?     optional
valid_from?                optional
valid_until?               optional
```

Examples:

Mathematics:

```text
Theorem Record
recorded_at = registration time
valid_from / valid_until usually absent
```

Policy:

```text
Policy Record
published_at = release date
valid_from   = effective date
valid_until  = repeal/replacement date
```

Engineering configuration:

```text
Specification Record
recorded_at  = when imported
valid_from   = configuration adoption date
valid_until  = supersession date
```

Historical assertion:

```text
Battle occurred
recorded_at = when Record was created
valid/event time = historical date being asserted
```

The temporal layer must remain domain-neutral while preserving these distinctions.

---

## 16. Events versus revisions

A revision means:

> the durable representation of an object changed.

An event means:

> something happened.

They are not interchangeable.

Examples of events:

```text
source published
policy entered force
company changed documentation
experiment performed
record challenged
relation retracted
paper withdrawn
specification superseded
```

An event may cause revisions, but the event can also be a first-class historical object with its own occurrence time and recording time.

Long-term Testamur should support explicit Event objects or an equivalent extension-defined representation for domain events that need durable identity.

Do not force all historical facts into revision metadata.

---

## 17. UI contract

The UI must clearly expose which temporal mode the user is viewing.

Bad:

```text
As of 2025-06-01
```

with ambiguous semantics.

Better:

```text
View:
[ Known by Testamur ] [ Publicly available ] [ Effective ]

Date: 2025-06-01
```

For retrospective items:

```text
Published in 2023
First captured by Testamur in 2028
```

For effective-time views:

```text
Effective: 2025-02-01 → 2025-08-31
Recorded by Testamur: 2025-03-20
```

The time slider in `TESTAMUR_UI_PRODUCT.md` should eventually bind to an explicit temporal mode rather than a generic timestamp.

---

## 18. History and diff naming

Canonical product diff terminology should remain mechanical.

Recommended names:

```text
state diff
revision diff
structural diff
relation diff
source diff
```

Avoid using `semantic diff` as the default public name when the implementation is actually comparing deterministic graph/state structure.

If model-generated interpretation is ever added, it should use an explicitly separate label such as:

```text
Derived interpretation
Model-generated summary
Non-authoritative semantic interpretation
```

The existing historical comparison API may retain compatibility internally, but future public API/UI naming should prefer `state_diff` or `structural_diff` for deterministic historical graph comparison.

---

## 19. API direction

A future temporal query surface may resemble:

```python
query.known_at(
    timestamp,
    perspective="testamur-cloud",
    scope="public",
)

query.available_by(
    timestamp,
    publication_policy="provenance_required",
)

query.effective_at(
    timestamp,
    scope="public",
)

query.temporal_view(
    known_at=record_cut,
    effective_at=world_time,
)
```

For graph traversal:

```python
query.dependencies(object_id, temporal_view=view)
query.impact(object_id, temporal_view=view)
query.provenance(object_id, temporal_view=view)
```

Every traversal must resolve objects and relations under the same temporal view.

No helper may silently fall back to current/latest state while a temporal view is active.

---

## 20. Storage direction

Do not duplicate existing immutable owners merely to add temporal indexing.

Preferred architecture:

```text
Core durable owners
  object revisions
  state revisions
  relation lifecycle
  source revisions / receipts
  events
        ↓
Temporal projection/index
  recorded_at index
  publication-time assertions
  validity intervals
  event-time projections
        ↓
Temporal query layer
  KNOWN_AT
  AVAILABLE_BY
  EFFECTIVE_AT
        ↓
UI / API / global graph
```

The temporal index is disposable/rebuildable where possible.

Authoritative identity and provenance remain in the underlying durable owners.

---

## 21. Indexing requirements

A scalable hosted implementation will likely need indexes over:

```text
(object_id, recorded_at)
(relation_id, recorded_at)
(source_id, retrieved_at)
(published_at)
(valid_from, valid_until)
(event_time)
visibility / workspace / project scope
```

For global projections, materialized temporal checkpoints may be introduced as an optimization.

They must remain disposable projections derived from immutable records rather than a new source of truth.

---

## 22. Fail-closed rules

The temporal layer must not:

- infer publication time from first retrieval time;
- infer effective time from publication time;
- infer observation time from source-declared metadata;
- expose late-arriving evidence inside an earlier `KNOWN_AT` view;
- rewrite an old project snapshot after a retrospective correction;
- treat a relation retraction timestamp as automatically equal to its represented `valid_until`;
- invent exact timestamps from year/month-only historical evidence;
- resolve historical queries through today's `latest` row;
- silently combine perspectives from different network nodes;
- present `AVAILABLE_BY` as proof that a specific person or project actually knew the material;
- present `EFFECTIVE_AT` as universal truth;
- allow model-generated temporal interpretation to overwrite observed timestamps.

---

## 23. MVP temporal layer

The first useful temporal implementation does not need the full global time machine.

### Phase 1

Implement explicit normalized projection of:

```text
recorded_at
published_at?     optional
valid_from?       optional
valid_until?      optional
```

for Source, Record, and Relation views where supported.

Add:

```text
KNOWN_AT(T)
```

for project-local/project-scoped graph queries, backed by existing immutable state/revision machinery.

### Phase 2

Add:

```text
AVAILABLE_BY(T)
EFFECTIVE_AT(T)
```

with provenance-bearing publication/validity assertions and late-arriving evidence handling.

### Phase 3

Add hosted-network temporal projection:

```text
GLOBAL_KNOWN_AT(T, perspective)
```

across public objects/relations without requiring one global revision DAG.

### Phase 4

Add UI time navigation across:

```text
Source history
Record neighborhood
Relations
Impact
Public graph
```

with explicit mode selection.

---

## 24. Acceptance scenarios

The temporal model is not complete until these scenarios produce different, correct answers.

### Scenario A — late paper

```text
paper published:       2023-04-01
first Testamur capture:2028-01-20
```

Required:

```text
KNOWN_AT(2024)     -> excluded
AVAILABLE_BY(2024) -> included with retrospective-discovery marker
```

### Scenario B — delayed-effective policy

```text
published: 2025-01-10
effective: 2025-02-01
captured:  2025-01-15
```

Required:

```text
KNOWN_AT(2025-01-20)     -> visible
AVAILABLE_BY(2025-01-20) -> visible
EFFECTIVE_AT(2025-01-20) -> not effective
EFFECTIVE_AT(2025-02-10) -> effective
```

### Scenario C — retrospective correction

```text
2025: Record A says event occurred in 2019
2027: new source supports 2018
```

Required:

```text
historical 2025 project view -> still shows A
current retrospective view   -> may show challenge/correction
```

### Scenario D — relation recorded late

```text
relation valid_from = 2024-01-01
relation recorded_at = 2026-01-01
```

Required:

```text
KNOWN_AT(2025)     -> relation absent
EFFECTIVE_AT(2025) under current retrospective knowledge -> relation may be present
```

### Scenario E — distributed observation

```text
Node A records source revision at 10:00
Node B receives it at 12:00
```

Required:

```text
KNOWN_AT(11:00, perspective=A) -> present
KNOWN_AT(11:00, perspective=B) -> absent
```

---

## 25. Product consequence

Once this model exists, Testamur can support three distinct historical experiences:

```text
1. Historical memory
   What did we know then?

2. Historical availability
   What could have been known then, according to evidence we have now?

3. Historical world/model state
   What was in force / effective then?
```

These should remain separate all the way from storage semantics to UI language.

That distinction is what turns Testamur from a versioned database into a real temporal provenance system.

---

## 26. Long-term formulation

The durable Testamur core can be summarized as:

```text
stable identity
+ immutable revision
+ typed relation
+ provenance
+ multiple notions of time
```

From those primitives, domain-specific systems can build:

```text
mathematical proof lineage
scientific evidence history
engineering specification history
policy and regulatory reconstruction
source / webpage revision history
organizational decision lineage
supply-chain monitoring
historical fact reconstruction
AI-generated work with inspectable provenance
```

The long-term “time machine” is therefore not a crawler feature and not a screenshot archive.

It is a queryable historical projection over provenance-bearing identities, revisions, relations, sources, and explicit time semantics.

> **Testamur should preserve not only what changed, but which past each query is asking for.**
