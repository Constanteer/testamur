# Testamur Codex plugin integration

> **Status:** clean-forwarded integration contract on the landed Testamur core.

The plugin uses Codex `SessionStart`, `PostToolUse`, and `SessionEnd` hooks. One active host attach epoch maps to one canonical Testamur WorkSession; ending the host session completes that WorkSession as `COMPLETED_UNRECONCILED`.

For Source Gateway calls, only structured `testamur.source-gateway.capture.v1` output is eligible for exact provenance. Source, Snapshot, and SourceRevision identities are re-resolved from the canonical local store before an exact `FETCHED` observation is written. JSON-looking text is never parsed as exact provenance.

Ordinary URL-bearing host tools create at most a redacted locator-level `DISCOVERED` candidate. Query strings, fragments, URL credentials, raw prompts, transcript content, raw tool input, and raw tool output are not persisted by this adapter.

Commands, patches, file operations, planning calls, and other non-source tools are not forced into Source semantics. Testamur command/runtime and artifact surfaces own those concerns.

```text
Codex observed tool call != exact source revision
canonical Gateway structured capture => exact FETCHED
FETCHED != durable reliance
durable reliance => explicit reconciliation only
```

The hook and MCP bootstrap share Testamur-owned state via `TESTAMUR_DB`, otherwise `$TESTAMUR_HOME/codex/evidence.db`, otherwise `~/.testamur/codex/evidence.db`.
