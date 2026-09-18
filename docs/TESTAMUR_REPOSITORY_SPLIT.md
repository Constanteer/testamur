# Testamur repository split

Status: **ready for owner-created destination repositories**.

The current `Constanteer/Mathub` repository is a transition workspace. Do not keep adding deployment/account/plugin ownership here merely because the code currently coexists.

The machine-readable boundary is `docs/TESTAMUR_REPOSITORY_SPLIT.json`.

## Target repositories

| Repository | Visibility | Owns | Must not own |
|---|---|---|---|
| `testamur-site` | public | landing site, pricing/legal, static deployment | Testamur stores, auth/billing runtime |
| `testamur` | public | semantic core, local runtime, CLI, local Web, release gates | hosted auth/tenant/billing |
| `testamur-plugins` | public | Codex plugin, MCP/agent/editor/tool adapters | second Testamur semantic implementation |
| `testamur-hosted` | private | hosted auth, accounts, billing, workers, managed persistence | alternate evidence/reliance truth |
| `Mathub` | owner decision | MathHub product and Lean-backed proof graph | Testamur as hidden runtime |

Dependency direction:

```text
testamur-site                 (product/publication only)

testamur-plugins ───────► testamur ◄────── testamur-hosted

MathHub                       (independent product)
```

## History-preserving extraction

Create the empty destination repositories first. Do **not** initialize them with README/license commits if you want the cleanest push of filtered history.

Use a disposable mirror/clone of the transition repository and `git filter-repo` for each extraction. Never run destructive filtering in the working clone you use for development.

### Site

```bash
git clone --mirror git@github.com:Constanteer/Mathub.git testamur-site.git
cd testamur-site.git
git filter-repo \
  --path site/ \
  --path tests/test_testamur_site_surface.py \
  --path-rename site/:
git remote add destination git@github.com:Constanteer/testamur-site.git
git push destination --all
git push destination --tags
```

The extracted repository root then directly contains `index.html`, legal pages, Dockerfile and nginx config. The site regression test remains under `tests/`; rename it to a site-owned test name after extraction if desired.

### Core / CLI

```bash
git clone git@github.com:Constanteer/Mathub.git testamur-core-extract
cd testamur-core-extract

git filter-repo \
  --path testamur/ \
  --path pyproject.toml \
  --path scripts/testamur_local_gate.sh \
  --path scripts/testamur_release_gate.sh \
  --path-glob 'tests/test_testamur_*.py' \
  --path-glob 'docs/TESTAMUR_*.md' \
  --path README.md \
  --path ARCHITECTURE.md \
  --path QUICK_LAUNCH.md

# These two tests belong to extracted site/plugins, not core.
git filter-repo \
  --path tests/test_testamur_site_surface.py \
  --path tests/test_testamur_codex_plugin_package.py \
  --invert-paths

git remote add destination git@github.com:Constanteer/testamur.git
git push destination --all
git push destination --tags
```

Before making this repository public, choose the OSS license and reconcile `0.3.0.dev0` with the first public tag. Do not silently call the same package both “0.1” and “0.3”.

### Plugins / tools

```bash
git clone git@github.com:Constanteer/Mathub.git testamur-plugins-extract
cd testamur-plugins-extract

git filter-repo \
  --path plugins/ \
  --path integrations/ \
  --path .agents/plugins/marketplace.json \
  --path tests/test_testamur_codex_plugin_package.py

git remote add destination git@github.com:Constanteer/testamur-plugins.git
git push destination --all
git push destination --tags
```

The extracted plugin repository keeps its repository marketplace catalog and plugin-package regression test. The first cleanup commit should add an explicit dependency on the public Testamur core. The existing Codex MCP launcher already imports installed `testamur` first; its monorepo-relative lookup is a development fallback, not the intended distribution contract.

Publication prep already lives under `plugins/testamur-codex/SUBMISSION.md` and `plugins/testamur-codex/submission-tests.json`. The current local MCP launcher is for local/repository marketplace use; public MCP submission requires a stable remote HTTPS endpoint. Do not fabricate authentication metadata while the plugin remains local-only.

Do **not** move `testamur.codex_gateway_hook` / `testamur.source_gateway_mcp` out of core during the history extraction itself. Relocate those compatibility entrypoints only in a tested follow-up so existing CLI/plugin launchers do not break during the split.

### Hosted

The current `apps/` tree is mainly a boundary marker, not the full production service plane. Create the private hosted repository separately, then selectively clean-forward hosted sync/account/billing work into it. Do not revive historical stacked branches wholesale.

## Transition-repository cleanup

After all destination repositories exist and their exact heads are validated:

1. make the destination repositories the canonical owners in their READMEs;
2. update links/package metadata in each new repository;
3. run Testamur release gates in the extracted core;
4. smoke the extracted plugin against an installed extracted core;
5. smoke the extracted site container;
6. only then remove Testamur/site/plugin/hosted-transition paths from MathHub.

The source repository remains useful as history. Deleting files from MathHub after extraction is not the same thing as deleting their Git history.

## Release rule during the split

The current Testamur main line is already exact-head release-gate green. Repository extraction should therefore be a boundary-preserving operation, not an excuse to change semantics.

If an extraction requires code changes, make those changes **after** extraction in the repository that will own them.
