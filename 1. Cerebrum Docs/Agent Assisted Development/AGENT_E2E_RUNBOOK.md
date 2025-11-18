# Agent and model context protocol end-to-end runbook

This runbook codifies how agents gain full control over the n00tropic Cerebrum workspace via Model Context Protocol (MCP) surfaces, matching the expectations in `AI_WORKSPACE_PLAYBOOK.md` and `PROJECT_ORCHESTRATION.md`.

## Surfaces and responsibilities

| Surface                | Location                                | Purpose                                                                                                                                            |
| ---------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Capability graph**   | `n00t/capabilities/manifest.json`       | Declares every automation entrypoint (workspace refresh, project orchestration, lifecycle radar, etc.). Agents call these through MCP Tools.       |
| **AI workflow MCP**    | `n00tropic/.dev/automation/mcp-server/` | Provides `run_workflow_phase`, `run_full_workflow`, and `get_workflow_status` Tools plus access to workflow artifacts and the capability manifest. |
| **Cortex catalog MCP** | `n00-cortex/mcp-server/`                | Exposes catalog JSON, starter templates, and documentation manifests as read-only resources for planning phases.                                   |
| **Docs MCP**           | `mcp/docs_server/`                      | Supplies documentation search/list/read utilities so agents can reference governing specs.                                                         |

## Installation checklist

1. Install Node packages once per workspace:

```bash
cd "n00tropic/.dev/automation/mcp-server"
pnpm install
cd "n00-cortex/mcp-server"
pnpm install
```

1. Provision the Python docs MCP server:

```bash
cd mcp/docs_server
pip install -r requirements.txt
```

1. Install the agent framework runtime (Python sample agents):

```bash
pip install agent-framework-azure-ai --pre
```

## Editor configuration for Copilot workflows

`.vscode/settings.json` now points the `ai-workflow` server at `n00tropic/.dev/automation/mcp-server/index.js`, ensuring Copilot Chat can load the Tools without path errors. The `cortex` server path already resolves to `n00-cortex/mcp-server/index.js`.

For other MCP-aware clients (Claude Desktop, Cline, etc.), add entries equivalent to:

```jsonc
{
  "mcpServers": {
    "ai-workflow": {
      "command": "node",
      "args": [
        "/Volumes/APFS Space/n00tropic/n00tropic-cerebrum/n00tropic/.dev/automation/mcp-server/index.js",
      ],
      "cwd": "/Volumes/APFS Space/n00tropic/n00tropic-cerebrum/n00tropic",
    },
    "cortex": {
      "command": "node",
      "args": [
        "/Volumes/APFS Space/n00tropic/n00tropic-cerebrum/n00-cortex/mcp-server/index.js",
      ],
      "cwd": "/Volumes/APFS Space/n00tropic/n00tropic-cerebrum/n00-cortex",
    },
    "n00-docs": {
      "command": "python",
      "args": [
        "/Volumes/APFS Space/n00tropic/n00tropic-cerebrum/mcp/docs_server/server.py",
      ],
      "cwd": "/Volumes/APFS Space/n00tropic/n00tropic-cerebrum",
    },
  },
}
```

## Agent orchestration flow

1. **Discovery:** Agent queries `get_workflow_status` for script/executable checks and inspects `n00t/capabilities/manifest.json` (exposed as `ai-workflow://capabilities/manifest`).
2. **Planning and architecture:** Use `n00-docs` + `n00-cortex` MCP servers to gather ADRs, manifests, and tag taxonomies.
3. **Execution:** Trigger capabilities via `run_workflow_phase` (interactive for planning, non-interactive for automation) or `run_full_workflow`. Script outputs are written to `.dev/automation/artifacts/ai-workflows/**` and referenced in follow-up MCP resource reads.
4. **Verification:** Re-run `get_workflow_status` and inspect `.dev/automation/artifacts/automation/*.json` for telemetry. For project orchestration tasks, follow `PROJECT_ORCHESTRATION.md` (capture → sync → preflight) using the same capability IDs.

## Sample agent skeleton in Python

```python
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from agent_framework.mcp import MCPTool
from agent_framework.observability import setup_observability

setup_observability(otlp_endpoint="http://localhost:4317", enable_sensitive_data=True)

client = OpenAIChatClient(
    model="openai/gpt-5",  # prefer GitHub-hosted GPT-5 for reasoning depth
)

agent = Agent(
    client=client,
    tools=[
        MCPTool(name="run_workflow_phase", server="ai-workflow"),
        MCPTool(name="run_full_workflow", server="ai-workflow"),
        MCPTool(name="get_workflow_status", server="ai-workflow"),
    ],
)

result = agent.run({
    "task": "Run workspace.preflight and share artifact paths",
    "context": "Use MCP Tools; prefer non-interactive execution"
})
print(result.output)
```

**Model choice**: `openai/gpt-5` (via GitHub Models) balances orchestration reasoning with manageable cost; switch to `openai/gpt-5-mini` when latency is critical.

## Telemetry and observability

- Workspace entry points (`cli.py`, `.dev/automation/scripts/workspace-health.py`, and `mcp/docs_server/server.py`) now import `observability.initialize_tracing`, enabling `agent_framework` telemetry whenever the dependency is installed.
- Node-based MCP servers (`n00tropic/.dev/automation/mcp-server/index.js` and `n00-cortex/mcp-server/index.js`) call `observability-node.mjs`, which configures OpenTelemetry with the OTLP gRPC exporter and wraps every MCP handler in spans. Install their package set once via `pnpm install --filter @n00tropic/ai-workflow-mcp --filter @n00tropic/n00-cortex-mcp` before launching clients.
- `OTEL_EXPORTER_OTLP_ENDPOINT` (default `http://127.0.0.1:4317`) and `OTEL_SERVICE_NAME` override the destination + logical service. Set `OTEL_ENABLE_SENSITIVE_DATA=true` when collectors run in hardened environments; leave unset otherwise.
- Toggle instrumentation with `N00_DISABLE_TRACING=1` if the automation runs where OTLP collectors are unavailable.
- The helper falls back when `agent_framework` is missing, so existing scripts keep functioning without the dependency.

To view traces locally, launch an OpenTelemetry collector (or Docker `otel/opentelemetry-collector`) pointing at Honeycomb/Jaeger, then run `cli.py` commands—the spans are emitted before any sub-command logic executes.

## Verification steps

1. **CLI Sanity**

   ```bash
   cd n00tropic/.dev/automation/mcp-server
   node index.js <<<' '
   ```

(Expect startup banners; stop after confirming no missing-path errors.)

1. **Tool Smoke Test**

   ```bash
   FORCE_NON_INTERACTIVE=true \
   npx @modelcontextprotocol/client call-tool \
     --server node n00tropic/.dev/automation/mcp-server/index.js \
     --name get_workflow_status
   ```

1. **Capability Execution**

   ```bash
   .dev/automation/scripts/workspace-health.sh --publish-artifact --json
   ```

   Ensure `artifacts/workspace-health.json` is created for downstream agents.

1. **Agent run telemetry:** Confirm `.dev/automation/artifacts/automation/agent-run-*.json` is written after invoking MCP Tools.

## Residual risks

- Capabilities that point outside this repo (one level up) require the super-root to exist locally; CI agents must mount `/Volumes/APFS Space/n00tropic/.dev/automation`. Fallback: override entrypoints via environment variables when running in isolated clones.
- Workflow scripts assume executable bits; rerun `chmod +x .dev/automation/scripts/ai-workflows/*.sh` if Git resets permissions.
- Keep `@modelcontextprotocol/sdk` aligned across servers to avoid protocol drift.

Following this runbook ensures agents can traverse every orchestration path (workspace health, project lifecycle, AI workflows, documentation references) using a consistent MCP interface.
