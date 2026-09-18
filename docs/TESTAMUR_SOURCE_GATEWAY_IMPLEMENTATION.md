# Testamur Source Gateway — local exact-revision implementation

> **Status:** clean-forwarded local exact-revision gateway on the landed Testamur 0.1 core.
>
> This document describes the landed post-0.1 local exact-revision Gateway. Semantic ownership remains with `TESTAMUR_CONVERGENCE.md`, `TESTAMUR_AGENT_WORKFLOW.md`, and the canonical Source / WorkSession stores.

## Implemented path

```text
agent / MCP host
    ↓
testamur.fetch
    ↓
SourceFetchPolicy
    ↓
bounded HTTP(S) retrieval
    ↓
exact response entity bytes
    ├── local CAS (sha256)
    └── SourceStore
          ├── Source
          ├── Snapshot
          └── SourceRevision
    ↓
optional canonical WorkSession observation
    ↓
content + provenance envelope returned to caller
```

The core implementation is `TestamurSourceGateway` in `testamur/source_gateway.py`.

## Current public surfaces

### CLI

`testamur-gateway` exposes:

```text
fetch <locator>
open-revision <revision-id>
source-status <source-id>
revalidate <source-id>
watch-refresh <watch-id>
```

The CLI defaults to `.testamur/evidence.db` and honors `TESTAMUR_DB`.

### MCP

`testamur-gateway-mcp` is a newline-delimited JSON-RPC stdio MCP server.

It exposes:

```text
testamur.fetch
testamur.open_revision
testamur.source_status
testamur.revalidate
testamur.watch_refresh
```

It serves both:

```text
2026-07-28  server/discover + per-request metadata era
2025-11-25  initialize/initialized compatibility era
```

No MCP SDK dependency is required by this first slice.

## Exact identity behavior

For a successful fetch:

```text
bytes B
  ↓ sha256
content_hash H
  ↓
SourceRevision R = identity(Source, H)
  ↓
Snapshot S = one immutable observation
```

Repeated captures of the same bytes therefore produce:

```text
Snapshot S1 ─┐
             ├── SourceRevision R
Snapshot S2 ─┘
```

A later byte change creates a different SourceRevision.

The bytes are retained separately in `TestamurBlobStore`; SourceStore records content identity but does not claim publication rights over retained material.

## WorkSession binding

If the gateway receives a `session_id`, the session must already exist and remain `OPEN`; this is checked before network access or durable Source side effects.

The Gateway uses the canonical `WorkSessionStore` / `AgentCapture` path:

```text
Source candidate
    ↓
exact SourceRevision available?
    ├── yes -> FETCHED observation + retrieval receipt ref
    └── no  -> DISCOVERED_ONLY; no fabricated FETCHED observation
```

A successful exact capture records the precise `SourceRevision` through a mechanical retrieval receipt. An unavailable Snapshot has no exact revision and therefore stays discovery-only.

The Gateway never creates durable Reliance and does not infer model cognition from retrieval.

Thus:

```text
exact Gateway capture => FETCHED
unavailable Gateway capture != FETCHED
FETCHED != durable reliance
```

Reliance remains owned by explicit reconciliation.

## Content returned to MCP clients

`testamur.fetch` and `testamur.revalidate` return provenance metadata plus captured content when the response is within `max_return_bytes`.

UTF-8 bytes are returned as text. Non-UTF-8 bytes are returned as base64. Larger retained responses remain in CAS and the tool response reports that content was captured but not returned to the model.

`testamur.open_revision` allows an already retained exact revision to be reopened under an explicit return-size bound.

## Watch refresh

`watch-refresh` / `testamur.watch_refresh` performs:

```text
Watch
  ↓
revalidate watched Source
  ↓
new immutable Snapshot
  ↓
mechanical Watch evaluation
  ↓
changed | unchanged | unavailable | recovered | not_assessable
  ↓
optional Alert
```

As elsewhere in Testamur:

```text
CHANGED != INVALID
```

and an Alert is an operational observation rather than a truth verdict.

## Retrieval policy currently enforced

The local fetch primitive enforces:

```text
HTTP(S) only
no embedded URL credentials
private/link-local/non-global destinations blocked by default
redirect revalidation
max redirect count
max response bytes
request timeout
ambient HTTP(S)_PROXY ignored
Accept-Encoding: identity
```

`--allow-private-network` / the corresponding MCP flag is an explicit local override. MCP policy arguments are validated server-side rather than trusting the advertised JSON Schema alone; malformed booleans, non-integral bounds, and non-finite timeouts fail closed.

This is still a **local alpha transport policy**, not the W7 hosted multi-tenant egress sandbox. In particular, production hosted retrieval must add stronger DNS/connection pinning, tenant policy, authentication, rate limits, abuse controls, and isolated network execution.

## Known gaps after this slice

1. Codex plugin packaging does not yet automatically register the Source Gateway MCP server.
2. Host-native browser/search paths can still bypass the gateway; these remain partial provenance and must surface as such.
3. The MCP server has no remote authentication because this slice is stdio/local only.
4. Retrieval receipts are represented by immutable Snapshot metadata rather than a separate first-class RetrievalReceipt object.
5. Large-document partial-region exposure is not yet modeled; capturing a full revision and returning only a bounded prefix must not be confused with whole-document model exposure.
6. Hosted sync, quotas, retained-byte accounting, billing, and egress workers remain private hosted/service-plane responsibilities.

## Acceptance invariants

Regression coverage must preserve:

```text
same bytes => same SourceRevision, different Snapshot
failed retrieval => no fabricated SourceRevision
CAS digest == Snapshot content_hash
open_revision verifies retained bytes
Gateway capture => FETCHED, not RELIED_ON
locator-only bypass != exact revision
Watch refresh emits operational state only
MCP tools/list order is deterministic
modern and legacy MCP lifecycle both remain parseable
```
