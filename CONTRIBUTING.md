# Contribution Guide

This workspace stitches together multiple submodules (cortex, frontiers, horizons, school, menon, plicate, n00t, clear-fusion, n00tropic). To avoid pointer drift and surprise migrations, follow these rules for **every change**:

## Branch & pointer hygiene

- Submodules must stay on their declared branch from `.gitmodules` (default `main`, `docs` for `n00menon`). Do **not** commit detached HEADs.
- After committing inside a submodule, push upstream immediately, then update the superrepo pointer and commit it. No “pending” local commits.
- Run `pnpm run qa:workspace:full` before merging; it enforces pointer sync, cross-repo drift, Trunk lint, and schema checks.

## Tooling & runtimes

- Node: `24.11.0` via `.nvmrc` and `scripts/sync-node-version.sh`; pnpm: `10.23.0` via corepack.
- Python: `3.11.8` for Trunk runtimes and sample contexts.
- Prefer subproject-local CI: `pnpm run validate` (Node/TS) or `uv run pytest/ruff/mypy` (Python). Use `pnpm run qa:workspace:full` only for sweeping upgrades.

## Lint/format policy

- Trunk is canonical; don’t diverge linters or pinned versions without adding an override manifest under `n00-cortex/data/dependency-overrides/`.
- Isort controls import ordering; Black sorting is disabled accordingly across Trunk configs.
- Tag/feature lists in frontiers exports are sorted to keep diffs deterministic.

## Dependency & template updates

- Renovate extends the workspace preset; keep it that way.
- When updating templates in `n00-frontiers`, re-export and run `pnpm -C n00-cortex ingest:frontiers -- --update-lock` to refresh catalogs.
- If you add or move docs, regenerate `data/catalog/docs-manifest.json` in cortex (`python3 scripts/generate_docs_manifest.py`).

## Elevation rule

- If a change alters shared standards (Trunk config, toolchain versions, template quality gates, contributor policy), **elevate upstream immediately**: update `n00-cortex` canonical copies and rerun workspace QA so submodules stay aligned.

## Local safety checks

- From the superrepo root: `pnpm run qa:workspace:full` (doctor + meta-check + Trunk sweep).
- Fast per-repo: `pnpm run validate` (Node) or `uv run ruff && uv run pytest && uv run mypy` (Python).

## Filing issues

- Prefer filing in the owning repo (per the submodule list above) and cross-link from the superrepo issue for traceability.

## Auto-sync helper

- To propagate this CONTRIBUTING file into each submodule root: `./scripts/sync-contributing.sh --write` (safe; only updates when content differs).

## Coverage policy

- Maintain a **minimum 85% line coverage** per repo and for the superrepo. New changes must keep or raise coverage; exceptions require explicit approval and a follow-up issue.
- JavaScript/TypeScript: run `pnpm run test -- --coverage` or `vitest --coverage` and ensure reports stay ≥85%.
- Python: run `coverage run -m pytest && coverage report` (or `python -m pytest --cov` if configured) and keep modules touched ≥85%.
- Mixed repos: run both JS and Python coverage where applicable. Document coverage deltas in PR descriptions.
- If coverage dips below 85%, add tests before merge or file a waiver with a remediation plan (tests in the next PR).
