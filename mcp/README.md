# Master MCP Suite (agents, Copilot, Codex)

This directory centralises all MCP endpoints we expect agents to use:

- `docs` — n00 Docs MCP server (read-only docs/search).
- `filesystem` — stdio server for file access scoped to the workspace.
- `memory` — key/value memory server.
- `n00t-capabilities` — MCP shim that wraps the n00t capability manifest into callable tools.
- Optional: `github`, `search` (Brave).
- Routing profile: `mcp/routing-profile.yaml` provides pattern→server mapping for CapabilityRouter (e.g., `docs._` → `docs`, `deps._` → `n00t-capabilities`).
- Additional servers wired in suite:
  - `ai-workflow` (.dev/automation/mcp-server/index.js)
  - `cortex-catalog` (n00-cortex/mcp-server/index.js)
  - `cortex-graph` (HTTP at <http://localhost:8787/mcp>)

## Quick start

```bash
cd /path/to/n00tropic-cerebrum
# Provision both virtual environments from the lockfiles (once per clone or after dependency bumps)
./mcp/provision-venvs.sh

# Make sure the MCP tools from .venv are available (or `source .venv/bin/activate`)
export PATH="$PWD/.venv/bin:$PATH"

# Start suite (docs + capability shim + proxy)
./mcp/start-suite.sh

# Health check (list servers; optional tools with RUN_TOOLS=1)
WORKSPACE_ROOT=$(pwd) ./mcp/health-suite.sh
# RUN_TOOLS=1 WORKSPACE_ROOT=$(pwd) ./mcp/health-suite.sh

# Quick smoke (parses config, lists capabilities, exercises docs.get_page)
WORKSPACE_ROOT=$(pwd) ./mcp/smoke-suite.sh

# Validate manifests (single module or entire federation)
python mcp/validate_manifest.py --manifest n00t/capabilities/manifest.json --json
python mcp/validate_manifest.py --federation mcp/federation_manifest.json
# Run module health commands declared in federation manifest
RUN_MODULE_HEALTH=1 WORKSPACE_ROOT=$(pwd) ./mcp/health-suite.sh
```

### VS Code / Copilot quick start

```bash
mkdir -p .vscode
ln -sf ../mcp/vscode.mcp.json .vscode/mcp.json
```

Then open Copilot Chat → Agent → Tools and click **Start** to launch `filesystem`, `memory`, `docs`, and `n00t-capabilities`. Uncomment optional servers (GitHub, search, ai-workflow, cortex-\*) in `mcp/vscode.mcp.json` when you have tokens or local services.

If VS Code still fails to launch the local Python servers, run the config validator:

```bash
# Checks the default ~/Library/.../mcp.json entries by default
python mcp/check-vscode-mcp-config.py

# Or point it at a custom config file
python mcp/check-vscode-mcp-config.py --config ~/.vscode/mcp.json
```

It verifies that the `docs` and `n00t-capabilities` entries reference real files inside this repo and that `WORKSPACE_ROOT` matches the repository path.

## VS Code / Copilot (Agent Mode)

Point VS Code to the master suite with a single config file:

`mcp/vscode.mcp.json` (copy/symlink to `.vscode/mcp.json`):

```jsonc
{
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "${workspaceFolder}",
      ],
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
    },
    "docs": {
      "command": "python",
      "args": ["${workspaceFolder}/mcp/docs_server/server.py"],
    },
    "n00t-capabilities": {
      "command": "python",
      "args": ["${workspaceFolder}/mcp/capabilities_server.py"],
    },
    // Optional (uncomment with tokens set):
    // "github": {
    //   "command": "npx",
    //   "args": ["-y", "@modelcontextprotocol/server-github"],
    //   "env": { "GITHUB_TOKEN": "${env:GITHUB_TOKEN}" }
    // },
    // "search": {
    //   "command": "npx",
    //   "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    //   "env": { "BRAVE_API_KEY": "${env:BRAVE_API_KEY}" }
    // }
  },
}
```

After saving, open Copilot Chat → Agent → Tools (🔧) → Start to launch the servers.

### Environment guardrails

The `./mcp/provision-venvs.sh` helper ensures the two MCP-facing virtualenvs stay in sync with the lockfiles:

```bash
# Minimal tooling for docs + capabilities
UV_BIN=/usr/local/bin/uv ./mcp/provision-venvs.sh
```

- `.venv` → `requirements.workspace.min.lock` (fast, used by docs/capability servers)
- `.venv-workspace` → `requirements.workspace.lock` (full stack for agents/tests)

Run it after pulling dependency bumps or onboarding a new machine to avoid missing-module errors the next time MCP servers launch.

## mcp-proxy federation

- Config file: `mcp/mcp-suite.yaml`
- Health/list tools: `mcp/health-suite.sh` (wraps `mcp-proxy list/tools`)
- Smoke tests: `mcp/smoke-suite.sh`
- Suite launcher: `mcp/start-suite.sh`
- CI sanity: `mcp/ci-sanity.sh` (health with tool listing + smoke)
- Routing sample: `mcp/router-shim.py` prints resolved servers using `routing-profile.yaml`
- External servers: see `mcp/external-servers.example.json` for common third-party MCP servers (Asana, Azure DevOps, Context7, Playwright/Chrome DevTools, Logfire, SonarQube, Tavily, fetch/git). Copy entries as needed and inject tokens via env vars—never hardcode secrets in repo configs.

## Capability federation manifest

- Source of truth: `mcp/federation_manifest.json` enumerates every module-level capability manifest along with per-module metadata and optional health commands.
- `python mcp/validate_manifest.py --federation mcp/federation_manifest.json` performs structural validation for each module. Pass `--module <id>` to scope the run or `--manifest <path>` for spot checks outside the federation.
- Add `--run-health` (or set `RUN_MODULE_HEALTH=1` before calling `mcp/health-suite.sh`) to execute the module health commands declared in the manifest.
- Use `--json` for CI-friendly machine output when diffing module inventories or piping summaries into other automation.
- Current modules:
  - `n00t-core` → core automation surface from `n00t/capabilities/manifest.json`.
    - Includes docs automation entrypoints such as `docs.build`, `docs.lint`, and `docs.verify`, wiring `.dev/automation/scripts/docs-*.sh` into MCP tools.
  - `n00-horizons` → governance/radar/preflight tools from `n00-horizons/mcp/capabilities_manifest.json`.
  - `n00-frontiers` → template validation + import smoke tests from `n00-frontiers/mcp/capabilities_manifest.json`.
  - `n00-cortex` → schema + export automation from `n00-cortex/mcp/capabilities_manifest.json`.
  - `n00tropic` → AI design generation + publishing from `n00tropic/mcp/capabilities_manifest.json`.
- To run just one module locally, pass `--module <id>` to `mcp/capabilities_server.py`, e.g. `python mcp/capabilities_server.py --module n00-horizons --list`.

### Capability discovery helpers

- Script: `python mcp/discover_capability_candidates.py`
  - Compares every entrypoint declared in the federation manifests with automation scripts under `.dev/automation/scripts` and `*/mcp/scripts`.
  - Reports unused scripts as candidate capabilities, grouped by suggested module, and lists scan roots for transparency.
  - Use `--format json` to feed CI or dashboards, `--include-root <dir>` to point at additional repos, and `--extensions` to widen/narrow eligible file types.
  - `--baseline <path>` (defaults to `mcp/capability_candidates.baseline.json` when present) compares the current results to the tracked candidate list, while `--fail-on-new` turns new entries into hard failures. Refresh the corpus intentionally with `--write-baseline <path>` after adding MCP coverage or reprioritising the backlog.
  - `mcp/health-suite.sh` runs the discovery script automatically (and the baseline check when the baseline file exists), so CI/agents fail fast whenever new automation crops up without a matching MCP plan.
  - Run it before onboarding a repo (e.g., `n00-school`) to spot scripts lacking MCP coverage and prioritise which ones to elevate next.

## Status

- Docs MCP: ready (make `mcp-dev` or run directly).
- Filesystem & Memory: ready (npm @modelcontextprotocol servers).
- GitHub / Brave: optional, off by default.
- n00t capabilities: placeholder only; hook in once the shim lands.
