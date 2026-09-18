# Testamur Object Contract

> **Status:** shared contract for local CLI/read/product surfaces.
>
> This document does not define a new truth model. It standardizes how Testamur evidence and operations objects are named and transported across machine-readable surfaces.

## 1. Why this contract exists

The CLI, local read API, future web UI and integrations must not independently invent object kinds, error shapes or wrappers around the same evidence.

The rule is:

```text
one evidence substrate
→ several presentation/transports
```

not:

```text
CLI truth
API truth
UI truth
```

## 2. Current durable object references

The current syntactically recognizable durable families are:

```text
tst:run:*                 kind = run
tst:obs:*                 kind = observation
tst:verification:*        kind = verification

tst:source:*              kind = source
tst:revision:*            kind = revision
tst:snapshot:*            kind = snapshot

tst:record:*              kind = record
tst:record-revision:*     kind = record_revision
tst:relation:*            kind = relation

tst:watch:*               kind = watch
tst:watch-revision:*      kind = watch_revision
tst:watch-eval:*          kind = watch_evaluation
tst:alert:*               kind = alert
```

Anything else supplied to an inspection/query surface is initially classified as:

```text
kind = target
```

A target may later resolve to an artifact path or domain/logical reference. Syntactic classification does **not** assert existence.

Implementation owner:

```text
testamur/contracts.py
```

Longer prefixes such as `tst:record-revision:*` and `tst:watch-revision:*` are classified before their shorter parent prefixes.

Historical `wtn:run:*` references are also recognized as durable run references for read/migration compatibility. They are not canonical for new writes; newly-created runtime runs use `tst:run:*`.

## 3. Source / Revision / Snapshot distinction

```text
Source
  persistent tracked identity

Revision
  exact content identity for one Source
  Source + SHA-256 digest

Snapshot
  one immutable observation event
  may point to one Revision
```

Therefore:

```text
Snapshot != Revision
```

Same bytes observed repeatedly:

```text
one Source
one Revision
multiple Snapshots
```

Changed bytes:

```text
one Source
multiple Revisions
multiple Snapshots
```

A metadata-only/unavailable observation may have a Snapshot without a content Revision.

Implementation and detailed contract:

```text
testamur/source_store.py
docs/TESTAMUR_SOURCE_HISTORY.md
```

The Source store deliberately does not automatically retain raw bytes. Exact local byte retention is a separate opt-in content-addressed layer.

## 4. Record / RecordRevision / Relation distinction

```text
Record
  persistent identity for an assertion/requirement/observation/etc.

RecordRevision
  one immutable statement/title/basis version

Relation
  one immutable first-class typed edge/provenance object
```

Therefore:

```text
Record != RecordRevision
Record statement != source bytes
Relation != truth
Relation != causality
```

Initial relation vocabulary:

```text
supports
depends-on
contradicts
supersedes
cites
```

Implementations and detailed contract:

```text
testamur/record_store.py
testamur/record_source.py
docs/TESTAMUR_RECORD_RELATION.md
```

## 5. Watch / Evaluation / Alert distinction

Watch belongs to the operations surface, not the canonical source truth surface.

```text
Watch
  persistent operational configuration identity

WatchRevision
  immutable configuration revision

WatchEvaluation
  immutable mechanical evaluation of a Source Snapshot transition

Alert
  immutable operational event emitted under a WatchRevision policy
```

Operational states/events do not change source truth semantics:

```text
changed       != false
unavailable   != false
recovered     != correct
not_assessable != failure
```

Implementation and detailed contract:

```text
testamur/watch_store.py
docs/TESTAMUR_WATCH_ALERT.md
```

## 6. Object reference shape

```json
{
  "kind": "observation",
  "ref": "tst:obs:...",
  "durable": true
}
```

`durable=true` means the reference belongs to a recognized durable identity family. It does not mean the referenced row was found in the current environment.

## 7. Machine object envelope

Read surfaces may wrap an existing evidence payload without changing its semantics:

```json
{
  "ok": true,
  "schema": "testamur.object.v1",
  "object": {
    "kind": "verification",
    "ref": "tst:verification:...",
    "durable": true
  },
  "data": {
    "...": "underlying store/query result"
  }
}
```

The wrapper is transport metadata. The underlying store/query remains authoritative for the payload.

## 8. Machine error envelope

Shared machine surfaces should converge on:

```json
{
  "ok": false,
  "schema": "testamur.error.v1",
  "error": {
    "code": "not_found",
    "message": "object does not exist",
    "details": {
      "ref": "tst:obs:..."
    }
  }
}
```

`details` is optional.

Human CLI renderers may use concise prose, but machine consumers should not be forced to parse prose or Python exception class names as an API contract.

## 9. Mechanical comparison and raw-byte boundary

Source Snapshot comparison can mechanically establish exact identity/hash change without raw content.

When exact bytes are deliberately retained locally, Testamur may use:

```text
testamur/blob_store.py
testamur/mechanical_diff.py
```

to produce reproducible exact text/binary identity comparison.

Possessing bytes does not imply publication or redistribution rights:

```text
bytes retained != may publish bytes
```

See `docs/TESTAMUR_MECHANICAL_COMPARE.md`.

## 10. Semantic invariants

Object transport must preserve these distinctions:

```text
recorded object        != verified conclusion
verification record    != universal truth assertion
stale                  != false
requires_revalidation  != invalid
observation            != causal attribution
recognized durable ID  != object exists
snapshot               != revision
revision changed       != semantic meaning changed
record                 != record revision
record statement       != source bytes
relation               != truth / causality
operational alert      != epistemic judgment
retained bytes         != publication rights
```

A temporal envelope must also preserve:

```text
recorded_at != published_at != valid/effective time
KNOWN_AT != AVAILABLE_BY != EFFECTIVE_AT
```

`testamur/source_store.py` exposes `latest_recorded_snapshot` deliberately rather than a generic `as_of`; temporal reconstruction belongs to the explicit temporal layer.

## 11. Integration direction

Worker 1 (graph) owns evidence/revalidation traversal semantics and should not reinterpret object transport.

Worker 2 (temporal) may project Source/Snapshot/RecordRevision events into explicit time modes but must not mutate historical object identity.

Worker 3 (CLI) should inspect durable families through the same `show` mental model where coherent and keep machine errors aligned with this contract.

Worker 4 (read API) should project these stores directly and must not reimplement Source, Record, Relation, Watch or Alert identity semantics.
