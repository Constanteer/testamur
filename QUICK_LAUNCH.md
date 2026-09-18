# Quick launch

Testamur is easiest to understand by running one complete dependency loop.

The goal of this guide is not merely to start the process. In roughly five minutes you should have:

```text
Project
  └─ one Monitor
       └─ one recorded Source revision
```

That is the minimum useful state from which Testamur can tell you that an upstream basis changed later.

## 1. Install

Testamur requires Python 3.11 or newer.

```bash
git clone https://github.com/Constanteer/testamur.git
cd testamur

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Check the local CLI:

```bash
testamur --help
testamur status
```

Start the local Web workspace:

```bash
testamur-web
```

Open the URL printed by the server.

## 2. Create a project

Choose **New project**.

Name the work rather than the dependency. For example:

```text
api-client
```

A Project is a container for related work. It may contain many independent Monitors.

## 3. Add one real dependency

Open the Project's **Monitors** tab.

Add something the work genuinely uses, for example:

```text
https://example.com/api/spec
```

or a repository / artifact / plugin-provided target when the relevant monitor provider is installed.

A Monitor is one operational watch. Its target resolves to a Source with stable identity.

## 4. Record the baseline

Choose **Refresh** for the new Monitor.

The first observation gives Testamur a concrete recorded state/revision. Future observations can now be compared to that baseline.

This distinction matters:

```text
URL / locator
    !=
recorded revision
```

The locator tells Testamur where to look. The revision tells later work what actually existed when Testamur looked.

## 5. When the source changes

A later manual or scheduled check may report:

```text
changed
unavailable
recovered
```

A change is a review trigger, not a verdict.

Keep these invariants in mind:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
```

Open the Source history to inspect recorded observations. Where reliance/lineage data exists, open **Impact** to see which downstream work may need attention.

## 6. Revalidate deliberately

If downstream work depended on the changed basis:

1. inspect the change;
2. decide whether the downstream result still holds;
3. update/re-run the work when necessary;
4. record the new review or result against the new basis.

That is the Testamur loop:

```text
exact basis
    ↓
upstream change
    ↓
affected work
    ↓
explicit revalidation
```

## 7. Add agent integrations

Once the manual loop is clear, connect agent hosts to the same local Source Gateway.

For exact-revision source access:

```bash
testamur-gateway
```

For MCP hosts, configure the local stdio command:

```text
testamur-gateway-mcp
```

Do not treat the MCP process as an interactive CLI; the host should start it over stdio.

The integration contract preserves another important distinction:

```text
EXPOSED_TO_MODEL != RELIED
```

## 8. State location

Optional environment overrides:

```bash
export TESTAMUR_HOME=/path/to/testamur-state
export TESTAMUR_DB=/path/to/evidence.db
```

## 9. Validate a checkout

Install pytest, then run:

```bash
python -m pip install -U pytest
bash scripts/testamur_local_gate.sh smoke
bash scripts/testamur_local_gate.sh release
```

`release` requires a clean tracked checkout so its result identifies an exact commit.
