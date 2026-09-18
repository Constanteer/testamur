# Testamur raw-byte retention and purge

Status: local alpha retention contract.

This layer answers one narrow question:

> When may Testamur remove an exact retained CAS byte object without deleting evidence identity or breaking another Source that still needs the same bytes?

It does **not** delete Source, Snapshot, Revision, Record, Relation, Watch, temporal evidence, or private display metadata.

## 1. Identity and bytes are different things

A captured or uploaded byte sequence participates in at least two independent structures:

```text
Evidence identity
Source -> Snapshot -> Revision(content_hash)

Local byte retention
sha256:<digest> -> .testamur/blobs/sha256/...
```

Purging the second must not rewrite the first.

After a successful raw-byte purge, Testamur still knows mechanically that a Snapshot referred to an exact SHA-256 identity. It may no longer be able to display or compare the original bytes locally.

```text
purged bytes != erased evidence event
purged bytes != false claim
purged bytes != revoked publication
```

## 2. The CAS is shared by digest

The local BlobStore is content-addressed. Two unrelated Sources can therefore reference the same physical byte object.

```text
Source A Revision -> sha256:X
Source B Revision -> sha256:X
                     |
                     `-- one CAS object
```

Deleting `sha256:X` because Source A requested purge would be incorrect while Source B still retains it.

For this reason Testamur does **not** treat Source ownership as blob ownership.

## 3. Authoritative references come from SourceRevision

Testamur does not maintain a second mutable table that pretends to be the canonical list of which Sources contain a digest.

Durable references are derived from immutable `testamur_source_revisions` rows.

Retention control is a separate append-only overlay:

```text
(source_id, content_hash) -> retain / release events
```

No retention event means `retain`.

This is fail-closed: a missing control-plane row must never make an existing evidence reference disappear.

## 4. Retention events

`testamur_blob_retention_events` records append-only owner actions:

```text
retain
release
```

Append order is authoritative. Events cannot be updated or deleted.

A `release` event means only:

> this Source no longer requires Testamur to retain the raw bytes for this digest.

It does not delete the Source or Revision.

A later `retain` event can reacquire the retention reference if the shared blob still exists. It does not promise to reconstruct bytes that have already been physically deleted.

## 5. Policy and event state compose

The Source access-policy history remains authoritative for whether purge is currently permitted.

Current raw-byte policy:

```text
retain
purge_on_request
```

A Source reference can become inactive for physical deletion only when all of the following are true:

```text
current policy exists
AND current policy is purge_on_request
AND latest retention event for that Source+digest is release
AND that release was recorded under the current policy revision
```

Otherwise the Source is an active blocker.

This matters for race safety. If an owner changes the policy to `retain`, that policy alone immediately blocks deletion even before the explicit retain event is appended.

Retention events carry the access-policy revision under which they were recorded. A release from an older policy epoch therefore fails closed after any later policy change, even if the current policy is again `purge_on_request`.

Only a new explicit purge action under the current policy revision creates an effective release. This epoch binding lives in the retention core rather than depending on one particular CLI or product-write path.

## 6. In-flight write claims

A second race exists between CAS write and durable Snapshot/Revision persistence:

```text
writer computes bytes
writer puts CAS object
<small window>
writer records Snapshot/Revision
```

Without coordination, purge could observe no durable reference during that window and delete bytes the writer is about to reference.

Retention-aware writers therefore create an operational in-flight claim before CAS materialization and remove it only after the capture operation leaves the evidence write path.

```text
claim(digest)
-> CAS put
-> Snapshot / Revision persistence
-> release claim
```

Claims are not evidence and may be deleted. A crashed process may leave a stale claim; the alpha fails closed and treats it as a purge blocker rather than guessing that deletion is safe.

## 7. Final deletion is serialized with new claims

Checking blockers and unlinking the file must itself be one critical section.

The purge path uses SQLite `BEGIN IMMEDIATE` while it:

1. verifies the latest owner policy;
2. appends or reuses the release event;
3. counts active durable references;
4. counts in-flight claims;
5. integrity-verifies and unlinks the CAS object when no blocker remains.

A retention-aware writer must insert a claim before writing the CAS. Its claim insertion cannot slip between the final blocker check and unlink.

The two safe orderings are therefore:

```text
purge wins lock -> delete -> commit -> writer claims -> writer recreates CAS
```

or

```text
writer claims -> purge sees claim -> bytes retained
```

## 8. Integrity before deletion

`TestamurBlobStore.delete_verified()` hashes the stored bytes before unlinking them.

If the physical file no longer matches its SHA-256 path, deletion fails with a storage-integrity error.

Testamur deliberately leaves the corrupt object in place rather than silently destroying evidence that the storage invariant was violated.

## 9. Local owner controls

CLI:

```bash
testamur source retention tst:source:... retain
testamur source retention tst:source:... purge_on_request
testamur source purge tst:source:...
```

Machine output remains `testamur.write.v1` / `testamur.error.v1`.

Local same-origin product write routes:

```text
POST /v1/write/sources/retention
POST /v1/write/sources/purge
```

The local alpha supplies the trusted owner subject `local:user`. Hosted deployments must replace this with authenticated tenant/user context; they must never accept owner identity directly from an untrusted request body.

## 10. Purge outcomes

Per digest, purge reports one of:

```text
deleted
already_absent
retained_shared_or_inflight
```

`retained_shared_or_inflight` is not an error. It means the Source's release was recorded, but another durable Source reference or active writer still requires the shared bytes.

A repeated explicit purge can later delete the object after those blockers disappear, provided the current policy still allows purge.

## 11. What remains after purge

Preserved:

```text
Source identity
Snapshot history
Revision digest identity
Record / Relation basis references
Watch / Alert history
Temporal evidence
owner-private filename/display metadata
retention event audit history
```

Potentially unavailable after physical deletion:

```text
exact raw bytes
byte-for-byte local diff requiring those bytes
local re-render/extraction requiring raw bytes
```

Private filename deletion is a separate erasable-metadata operation and is intentionally not coupled to raw-byte purge.

## 12. Non-goals of this slice

Not implemented here:

```text
hosted authentication / authorization
multi-tenant object-store deletion
backup / replica erasure propagation
automatic retention schedules
stale-claim garbage collection
legal-hold policy
whole-account deletion workflow
Source/Snapshot/Revision deletion
cryptographic erasure keys
```

Those require a hosted control plane and stronger lifecycle semantics. The local alpha must not imply they already exist.
