# Testamur Record / Relation Kernel

> **Status:** implemented local kernel contract for the early Record → Basis → Relation product slice.

Implementations:

```text
testamur/record_store.py
testamur/record_source.py
```

## 1. Record vs RecordRevision

```text
Record
  persistent identity across changes

RecordRevision
  one immutable declared statement/title/basis revision
```

Durable IDs:

```text
tst:record:...
tst:record-revision:...
```

Editing a Record means appending a new RecordRevision. Old revisions are never updated or deleted.

The append API requires an `expected_parent_revision_id`. This is an optimistic concurrency boundary: a stale client must not silently overwrite a newer logical head.

## 2. Statement is not source bytes

A Record statement may normalize or express something derived from source evidence.

Therefore:

```text
Record statement != Source Revision bytes
```

The immutable RecordRevision explicitly records this semantic distinction.

Recording a statement does not imply that it is true.

## 3. Basis

Basis is an ordered list of declared typed references.

Each entry minimally requires:

```text
kind
ref
```

Domain-specific fields are allowed when mechanically serializable.

Examples:

```json
{
  "kind": "source_revision",
  "ref": "tst:revision:...",
  "snapshot_ref": "tst:snapshot:...",
  "region": {"kind": "section", "value": "4.2"}
}
```

or domain-specific basis such as:

```text
axiom
definition
observation
measurement
dataset
protocol
requirement
constraint
standard
test result
primary source
archival record
```

Testamur does not imply equal epistemic force among basis kinds.

## 4. Create Record from Source Revision

`create_record_from_source_revision(...)` validates that:

```text
pinned tst:revision:* exists
optional tst:snapshot:* exists
optional Snapshot belongs to the same Source
optional Snapshot observes the exact pinned Revision
```

It then persists an exact basis reference containing:

```text
source_ref
source revision ref
exact content hash
optional snapshot ref
optional observation time
optional region selector
```

The region is preserved as declared selector provenance. Generic Testamur does not pretend that one region representation has universal semantics across HTML, PDF, audio, source code, mathematics, etc.

## 5. Mechanical revision comparison

Record revision comparison can report exact mechanical differences such as:

```text
statement changed
title changed
basis list changed
```

It does not infer:

```text
semantic equivalence
truth change
which statement is better
```

## 6. Relations are first-class objects

A canonical relation is an inspectable immutable object, not merely a rendered graph line.

Durable ID:

```text
tst:relation:...
```

Initial relation vocabulary is intentionally small:

```text
supports
depends-on
contradicts
supersedes
cites
```

A Relation records:

```text
relation type
from_ref
to_ref
basis
created_by (declared provenance)
recorded_at
```

Relation recording does not imply truth or causality.

AI extraction must not silently create canonical relations without an explicit recorded relation event/boundary.

## 7. Relation projections

`relations_for(ref, ...)` is a bounded projection over immutable Relation objects.

The graph UI may render these objects as edges, but the underlying Relation remains independently inspectable.

## 8. Append-only rule

Record, RecordRevision and Relation tables reject UPDATE/DELETE.

State changes that need lifecycle semantics later should use explicit append-only events/supersession rather than in-place mutation of historical evidence.
