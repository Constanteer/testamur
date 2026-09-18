# Testamur Mechanical Compare

> **Status:** implemented local comparison substrate for exact retained bytes.

Implementations:

```text
testamur/blob_store.py
testamur/mechanical_diff.py
```

## 1. Why byte storage is separate from Source identity

`testamur/source_store.py` deliberately records Source / Revision / Snapshot identity and digests without automatically retaining raw content.

That separation is important:

```text
retrieved bytes != right to publish bytes
hash known       != content may be redistributed
Source tracked   != Testamur must mirror raw content
```

For local/self-hosted workflows that need exact mechanical diff, Testamur provides an **opt-in local content-addressed blob store**.

The blob store is storage/integrity infrastructure, not publication policy.

## 2. Content-addressed local blobs

Blob identity is:

```text
sha256:<64 hex>
```

Storage is keyed by that exact digest. Re-storing identical bytes reuses the same local object.

Writes use a temporary file, flush/fsync, atomic replace and a post-write digest check. Reads verify digest identity and fail closed on corruption.

The blob API explicitly reports:

```text
publication_rights_implied = false
```

A future visibility/rights layer decides whether content may be rendered, shared, exported or served to another principal.

## 3. Mechanical comparison

`compare_blobs(...)` compares exact locally retained byte identities.

### Identical

If both sides have the same SHA-256:

```text
kind = identical
same_exact_content = true
```

No diff computation is necessary.

### Text

If both blobs fit the configured byte budget and decode under the requested encoding, Testamur produces a deterministic unified diff with mechanical addition/deletion counts.

The canonical result is based on exact retained bytes and configured context lines.

### Binary / undecodable

If decoding fails:

```text
kind = binary
```

Testamur still reports exact hashes/sizes but does not fabricate a text diff.

### Too large

If either side exceeds the inline comparison budget:

```text
kind = too_large_for_inline_diff
```

The result remains mechanically explicit rather than silently loading unbounded content.

## 4. Semantic boundary

Mechanical diff may establish facts such as:

```text
exact bytes differ
these lines were added/removed
byte size changed
```

It does **not** establish:

```text
meaning changed
policy became stricter
claim became false
new version is better
```

Model-generated or domain-specific semantic interpretation, if later added, must be a separately identified derived view with the mechanical diff still inspectable underneath.

## 5. Source integration

A captured Source Snapshot may carry a content hash matching a locally retained blob.

The association is mechanical because both are SHA-256 content identities. The current Source store does not require blob retention; absence of a blob does not invalidate the Source Revision identity.

This permits deployments such as:

```text
public metadata-only history
private/local exact bytes
licensed provider re-fetch
short-retention raw content
full self-hosted archive
```

without changing Source / Revision / Snapshot identity semantics.

## 6. Security/integrity behavior

Blob corruption is not treated as an ordinary cache miss. If bytes exist at a content-addressed path but no longer hash to that identity, reads fail with an integrity error.

Inline diff byte budgets should remain bounded. A future network read surface must add authorization and response-size controls before exposing stored bytes.
