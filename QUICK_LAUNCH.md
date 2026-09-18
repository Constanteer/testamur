# Quick launch

## 1. Install

Testamur requires Python 3.11 or newer.

```bash
git clone https://github.com/Constanteer/testamur.git
cd testamur

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## 2. Check the local CLI

```bash
testamur --help
testamur status
```

## 3. Start the local Web workspace

```bash
testamur-web
```

The Web interface uses the same canonical Testamur state as the CLI.

## 4. Source Gateway

For exact-revision source access:

```bash
testamur-gateway
```

For MCP hosts, configure the local stdio command:

```text
testamur-gateway-mcp
```

Do not treat the MCP process as an interactive CLI; the host should start it over stdio.

## 5. State location

Optional environment overrides:

```bash
export TESTAMUR_HOME=/path/to/testamur-state
export TESTAMUR_DB=/path/to/evidence.db
```

## 6. Validate a checkout

Install pytest, then run:

```bash
python -m pip install -U pytest
bash scripts/testamur_local_gate.sh smoke
bash scripts/testamur_local_gate.sh release
```

`release` requires a clean tracked checkout so its result identifies an exact commit.

The semantic invariants remain:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
lineage != affectedness verdict
```
