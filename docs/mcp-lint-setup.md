# MCP Lint & Dependency Ops (VS Code/Copilot ready)

AGENT_HOOK: dependency-management

This guide shows how to expose the workspace Trunk lint runner (and dependency ops) to MCP-capable clients such as VS Code Copilot / Codex, with setup separated from lint execution.

## Capabilities

- `deps.trunkLint` (MCP) → runs `trunk check` (default `--changed`; supports `scope: all` and `filter` for linters) via `.dev/automation/scripts/trunk-lint-run.sh`, returning a log path under `artifacts/trunk/`.
- `deps.drift`, `deps.sbom`, `deps.audit`, `deps.renovateDryRun` (existing) — available via MCP as documented in `docs/dependency-management.md`.

## Prereqs

- Trunk CLI installed (CI auto-installs; locally run `.dev/automation/scripts/trunk-lint-setup.sh` with `TRUNK_INSTALL=1` to install and init without running lint).
- Node/pnpm + Python per workspace (use `scripts/sync-venvs.py` / `pnpm install -w`).
- Syft auto-fetches when missing via `deps-sbom.sh`.

## VS Code / Copilot MCP config (example)

In your VS Code `settings.json` (or Copilot MCP config), add:

```jsonc
"github.copilot.mcp.servers": {
  "n00t": {
    "command": "python",
    "args": ["${workspaceFolder}/n00t/cli/index.ts"],
    "env": {
      "WORKSPACE_ROOT": "${workspaceFolder}",
      "PATH": "${workspaceFolder}/bin:${env:PATH}"
    }
  }
}
```

Then call tools:

- `deps.trunkLint` with payload `{ "scope": "changed" }` or `{ "scope": "all", "filter": "ruff,biome-lint" }`.
- `deps.drift` with `{ "format": "json" }`, etc.

## Running locally (CLI)

```bash
# lint changed files
# one-off setup (installs trunk and inits .trunk/ if missing)
TRUNK_INSTALL=1 .dev/automation/scripts/trunk-lint-setup.sh

# lint changed files
TRUNK_CHECK_SCOPE=changed .dev/automation/scripts/trunk-lint-run.sh

# lint everything with filters
TRUNK_CHECK_SCOPE=all TRUNK_CHECK_FILTER="ruff,biome-lint,eslint" .dev/automation/scripts/trunk-lint-run.sh
```

## Guarantees against regressions

- Each repo keeps its own `.trunk/trunk.yaml`; the scheduled workflow `.github/workflows/trunk-upgrade-recursive.yml` upgrades plugins per repo and auto-inits missing configs without overwriting existing ones.
- Drift CI runs with `--fail-on any` to prevent dependency divergence.
- MCP `deps.trunkLint` surfaces lint logs via MCP so agents (and Copilot) see live issues during iterations. Setup is decoupled; use `trunk-lint-setup.sh` once per machine as needed.
