# Testamur

Private split-test snapshot of the Testamur semantic core, local runtime, CLI and local Web.

Canonical loop:

```text
SourceRevision
  -> WorkSession
  -> explicit reconciliation
  -> Policy
  -> Reliance
  -> Watch/change
  -> impact / affectedness
  -> revalidation
```

Semantic invariants include:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
lineage != affectedness verdict
```

This repository was clean-snapshotted from `Constanteer/Mathub@78b40a7a921b6d8b44f3c5fa5e39d31ba74cb6e8` for private split testing. No pre-split Git history is retained.
