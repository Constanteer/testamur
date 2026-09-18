# Testamur environment

Testamur is not primarily a database CLI. It is an evidence environment that surrounds ordinary work.

The user should keep doing normal work. Testamur records what happened, what the work depended on, what was actually checked, and what becomes uncertain when an input or dependency changes.

## Core interaction model

The public CLI is intentionally small:

```text
testamur init
testamur status
testamur run
testamur show
testamur why
testamur trace
testamur verify
testamur impact
```

Everything else belongs in adapters, policy, admin surfaces, or plumbing APIs.

The shortest normal workflow is:

```bash
testamur init
testamur -- pytest
```

`testamur -- <command>` is shorthand for `testamur run -- <command>`.

The public help surface also exposes graph inspection directly:

```bash
testamur show result.json
testamur trace result.json --recursive
testamur impact raw.csv --recursive --max-depth 8
```

## Project environment

Initialization creates a local environment:

```text
repo/
  .testamur/
    environment.json
    testamur.sqlite3
```

Commands search upward from the current directory for `.testamur/environment.json`, so every subdirectory of the project shares the same evidence environment.

Testamur adds the environment directory to the repository-local `.git/info/exclude`. It does not silently edit the tracked `.gitignore`.

## Brand and compatibility boundary

`Testamur` is the user-facing product and command namespace.

The existing `witness.*` Python package remains the compatibility/runtime core during the migration. This avoids a high-risk package-wide rename while the protocol, durable store, command execution, idempotency, evidence graph, and historical bundles remain compatible.

New user-facing work should use Testamur terminology. New core protocol identifiers should only be renamed when a versioned migration exists.

## Epistemic rule

Recording is not verification.

A successful command may establish that:

- a particular process ran;
- against particular declared or observed inputs;
- from a particular Git/worktree state;
- and produced particular observed outputs.

It does not by itself establish that the result is correct.

The CLI therefore says:

```text
This run produced evidence, not verification.
```

Verification must be represented as a separate mechanically inspectable event or relation.

The same distinction applies to graph traversal:

```text
changed input
  -> dependent evidence requires revalidation
  != downstream conclusion is false
```

A recorded temporal or declared relationship is also not silently promoted into causal attribution.

## Durable object model

The local environment contains inspectable durable identities rather than only human-readable log output.

Current public object families include:

```text
wtn:run:*             durable command/run receipt
tst:obs:*             immutable artifact observation
tst:verification:*    immutable checker binding
```

`testamur show <id>` can inspect these objects directly. Artifact paths are also valid inspection targets.

Examples:

```bash
testamur show wtn:run:...
testamur show tst:obs:...
testamur show tst:verification:...
testamur show build/result.json
```

Verification records are immutable. Their stored checker result does not change when a target changes; instead, inspection decorates the record with its current revision relationship such as `current` or `stale`.

## Evidence graph

The durable graph is built from persisted observations. Querying historical provenance must never reconstruct history by re-snapshotting the current worktree.

The core shape is bipartite:

```text
artifact revision
  <- output/worktree observation
  <- run
  <- input observation
  <- artifact revision
```

A run may therefore connect observed input revisions to observed outputs without claiming that every observed output was causally produced by every input.

### Revision-aware edges

Path equality is not enough to connect evidence.

```text
mid.txt@hash_A  !=  mid.txt@hash_B
```

When both sides of a candidate edge have content hashes:

- matching hashes form a traversable revision edge;
- different hashes are retained as historical mismatch evidence but are not traversed;
- a missing hash is `not_assessable`, not silently treated as equal.

This prevents an old producer of `result.csv@v1` from being attached to a later consumer that actually read `result.csv@v2` merely because the path string is the same.

### Recursive traversal

The default commands preserve their compact one-hop behavior. Recursive graph traversal is explicit:

```bash
testamur trace result.json --recursive
testamur impact raw.csv --recursive
testamur impact raw.csv --recursive --max-depth 4
```

Recursive traversal is bounded and cycle-safe. Results expose whether the requested depth or status traversal budget truncated the graph.

`trace` walks upstream observed provenance. Known revision mismatches are exposed separately as skipped historical producer revisions.

`impact` walks downstream reliance. It propagates the need to revalidate through revision-compatible persisted evidence edges. Known revision mismatches are exposed separately and do not propagate revalidation.

## Environment semantics

### `testamur init`

Create or discover the project evidence environment. The command should be idempotent.

### `testamur status`

Answer: "What evidence environment am I currently standing in?"

The current status surface reports separate dimensions rather than a score:

- durable run and observation counts;
- current verification state per target;
- changed observed-input paths;
- runs directly requiring revalidation;
- runs transitively requiring revalidation;
- the total revalidation set;
- affected downstream observations and paths;
- whether dependency traversal was truncated by its path/depth budget.

Status uses the same revision-aware persisted graph as `impact --recursive`. A transitive revalidation result means the supporting evidence chain should be checked again; it does not assert that the downstream conclusion is false.

### `testamur run`

Execute work through the durable runtime and capture provenance.

Typical use:

```bash
testamur -- pytest
testamur run --worktree-delta -- codex exec "fix the parser"
testamur run --input raw.csv --output result.csv -- python experiment.py
```

The environment should make provenance the default and extra ceremony optional.

### `testamur show`

Inspect a durable run, artifact, observation, or verification record.

### `testamur why`

Answer why the target is believed, including supporting evidence and verification state.

### `testamur trace`

Trace production/provenance upstream. `--recursive` walks the persisted graph transitively; `--max-depth N` bounds the traversal.

### `testamur impact`

Trace downstream reliance and identify what requires revalidation when the target changes. `--recursive` propagates revalidation through compatible persisted revisions without converting uncertainty into invalidity.

### `testamur verify`

Request or execute an appropriate checker and bind its result to the target revision captured before checker execution.

A checker pass is scoped evidence for that checker and target revision. A checker failure is also scoped evidence; it does not automatically assert that the target is universally false.

When several checker records exist for the same current target revision, the latest current checker determines the target's current verification state. Historical records remain available for audit.

## Human and machine surfaces

Human-readable output is the default.

Automation uses:

```bash
testamur --json ...
```

`--json` may appear before or after the Testamur subcommand as long as it is before the `--` separator for a wrapped command. Tokens after `--` belong to the wrapped executable and are not rewritten.

The JSON surface should remain stable and explicit while the human renderer may improve rapidly.

## Status and traversal budgets

Ambient evidence systems eventually accumulate large graphs. Interactive status must therefore be bounded.

Current status propagation has explicit path and depth budgets. Exceeding either does not produce a fake complete result; it sets the dependency traversal to `truncated`.

The intended rule is:

```text
bounded evidence with explicit incompleteness
  > unbounded latency
  > silently incomplete evidence
```

## Long-term model

The environment should eventually become ambient enough that agents and tools use Testamur as an execution/evidence protocol rather than inventing prose claims about what they verified.

The desired loop is:

```text
work
  -> observation
  -> evidence
  -> verification
  -> reliance
  -> change
  -> invalidation / revalidation
```

More precisely, the current implementation avoids treating every change as invalidation. The mechanically defensible loop is closer to:

```text
work
  -> immutable observations
  -> revision-scoped evidence
  -> checker evidence
  -> reliance graph
  -> revision change
  -> direct + transitive revalidation set
  -> new evidence
```

Language and UI explain that graph. The graph is the durable substrate.
