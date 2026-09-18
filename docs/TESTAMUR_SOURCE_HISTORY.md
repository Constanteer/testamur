# Testamur Source History Kernel

> **Status:** implemented local kernel contract for the early Source → Revision → History → Compare product slice.

Implementation:

```text
testamur/source_store.py
```

## 1. Three identities, not one

```text
Source
  persistent tracked identity

Revision
  exact content state for one Source
  identified by Source + SHA-256 exact-content digest

Snapshot
  one immutable observation/capture event
  optionally points to one Revision
```

Therefore:

```text
Snapshot != Revision
```

Repeated observation of unchanged bytes produces:

```text
1 Source
1 Revision
N Snapshots
```

Changed bytes produce another Revision while preserving old Snapshot/Revision identity.

A failed/unavailable/metadata-only observation may create a Snapshot without a Revision.

## 2. Source identity

Default local source identity is derived from the **exact initial locator string**.

Testamur does not silently infer:

```text
URL normalization equivalence
redirect equivalence
mirror equivalence
renamed-domain equivalence
```

Those are future explicit alias/provenance relations, not string-cleaning tricks.

A Source ID is:

```text
tst:source:...
```

## 3. Revision identity

A strong Revision requires:

```text
sha256:<64 hex>
```

When bytes are supplied directly to the source store, the digest is computed from the exact bytes and the Snapshot records:

```text
digest_basis = computed_from_exact_bytes
```

When a digest is supplied without bytes, the Snapshot explicitly records:

```text
digest_basis = declared_digest
```

Declared and computed digests are not silently treated as the same observation boundary even when their values match.

Revision ID:

```text
tst:revision:...
```

Revision identity is scoped to the Source. Identical bytes observed at two different Sources do not collapse the Source identities or Source Revision identities.

## 4. Snapshot identity

Snapshot ID:

```text
tst:snapshot:...
```

A Snapshot records, at minimum:

```text
source_id
revision_id | null
locator
observed_at
recorded_at
status
content_hash | null
digest_basis
byte_size | null
retrieval_metadata
```

The store does not persist source raw bytes. Raw-content retention and redistribution are separate policy/rights/storage concerns.

Old Snapshots never redirect to the current Revision.

## 5. Time boundary

The source store exposes:

```text
latest_recorded_snapshot(source_id)
```

not a generic `as_of` query.

This is deliberate. It means latest capture according to local recording order.

Temporal reconstruction belongs to the explicit temporal model:

```text
KNOWN_AT(T)
AVAILABLE_BY(T)
EFFECTIVE_AT(T)
```

Worker 2 may project Source/Snapshot events into that layer, but must not mutate historical Source/Revision/Snapshot rows.

## 6. History and pagination

History is ordered by:

```text
recorded_at DESC, snapshot_id DESC
```

Storage-level pagination uses an exclusive tuple cursor:

```text
(recorded_at, snapshot_id)
```

Transport encoding of that cursor belongs to the read/API layer.

## 7. Compare

`compare_snapshots(left, right)` is mechanical identity comparison only.

It may report:

```text
exact hashes differ
same Revision ID
comparison not assessable because one side has no digest
```

It does not infer:

```text
semantic meaning changed
which version is correct
whether a downstream Record is false
```

Canonical semantic diff, if ever added, is a separate explicitly derived/non-authoritative layer.

## 8. Append-only rule

Source, Revision and Snapshot tables reject UPDATE and DELETE.

A new observation creates a new Snapshot. A changed content state creates a new Revision. Historical identity is not rewritten in place.
