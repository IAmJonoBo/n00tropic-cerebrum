# Scripts overview

Canonical entry points (use these first):

- `pnpm-migrate.mjs`: orchestrates npm→pnpm migration helpers (find, replace-npm, replace-npx, or `all`).
- `setup-pnpm.sh`: prepare pnpm (pinned 10.23.0) via corepack with npm fallback.
- `sync-trunk-defs.mjs` / `.dev/automation/scripts/sync-trunk.py`: keep Trunk configs in sync; prefer the Python version when running from CI.
- `find-npm-usages.mjs`: fast scan for stray npm commands (used by `pnpm-migrate find`).
- `remove-nx-cache.sh`: clean Nx cache across the workspace.
- `lint-python.mjs`: workspace Python lint orchestrator (ruff/black/isort) invoked by CI.
- `validate-docs.mjs`: Antora/markdown validation wrapper.

Deprecated in favor of `pnpm-migrate`:

- `replace-npx-with-pnpm.mjs`
- `replace-npm-commands-with-pnpm.mjs`
- `find-npm-usages.mjs` (still callable directly but prefer `pnpm-migrate find`)

Notes:

- Scripts assume toolchain pins tracked in `.nvmrc` (currently Node 24.11.1), pnpm 10.23.0, Python 3.11.14, and Go/Trunk 1.25.4. Update `.nvmrc` + `n00-cortex/data/toolchain-manifest.json` together so local shells and CI stay aligned.
- Avoid editing under `node_modules`, `.pnpm`, `dist`, or `artifacts`; most scripts skip these directories already.
