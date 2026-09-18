# Testamur private Source uploads

Status: **post-0.1 clean-forward candidate**.

This slice adds local user-file ingestion without changing Testamur evidence semantics or introducing hosted authentication.

## Core model

A local file upload creates:

```text
exact bytes
  -> local content-addressed Blob
  -> private Source
  -> immutable Snapshot
  -> exact SourceRevision
```

Access/privacy state is deliberately separate:

```text
Source identity
  != access policy
  != erasable filename/media-type convenience metadata
  != publication rights
```

## Private by default

Initial user-file ingestion always creates a private access-policy revision. A caller cannot pass `visibility=public` to the ingestion primitive; publication requires a later explicit access-policy revision.

Missing policy is fail-closed.

`allow_external_processing` defaults to false and must be an actual boolean.

## Path and metadata boundary

The caller's filesystem path is never used as Source identity and is never written into immutable Snapshot/Revision provenance.

A random opaque locator such as `upload:<nonce>` is supplied to the canonical SourceStore; SourceStore remains the owner of `tst:source:*` identity generation.

Filename and media type live only in `TestamurPrivateSourceMetadataStore`. They are mutable/erasable convenience metadata and are not part of Source/Snapshot/Revision identity.

Immutable upload Snapshot metadata records only privacy-safe capture facts such as upload kind, byte size, and explicit flags that filename/media type/local path were not persisted there.

## Raw bytes

Exact bytes are retained by `TestamurBlobStore`, keyed by SHA-256. Blob metadata does not expose a filesystem path.

Byte possession does not imply publication or redistribution rights.

Reference-aware purge/retention is implemented by `TestamurBlobRetentionStore`. Durable SourceRevision references, current policy revisions, append-only retain/release events, and in-flight ingest claims all participate in the deletion decision; raw bytes are never deleted merely because one Source requested purge.

## CLI

```bash
testamur source upload <file>
testamur --json source upload <file>
```

The local CLI uses owner subject `local:user` by default. `TESTAMUR_OWNER_SUBJECT` or `--owner-subject` may override the trusted local subject.

CLI output may show the basename back to the local user, but it must not echo the original parent path into durable provenance or machine errors.

## Semantics

```text
upload != publication
retained bytes != redistribution rights
private metadata != evidence identity
filename change/delete != new SourceRevision
external processing opt-in != truth/verification
evidence != truth
```

## Validation

The canonical release gate includes:

- private-by-default upload;
- local-path non-persistence;
- erasable filename metadata without identity changes;
- initial-public rejection before Source/policy persistence;
- append-only access policy order;
- fail-closed missing policy;
- explicit external-processing opt-in;
- oversize rejection before persistence;
- mutable media type excluded from immutable Snapshot;
- CLI machine output and missing-file error privacy.

The hosted authentication/tenant boundary, backup/replica erasure propagation, legal holds, and account-wide deletion remain separate service-plane work. Local reference-aware raw-byte purge is covered by `docs/TESTAMUR_BLOB_RETENTION.md`.
