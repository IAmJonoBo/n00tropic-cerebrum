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

1. Bootstrap shared workspace dependencies (PyYAML, jsonschema, docs MCP helpers):

```bash
cd /Volumes/APFS\ Space/n00tropic/n00tropic-cerebrum
scripts/bootstrap-python.sh
source .venv-workspace/bin/activate  # repeat in new shells before running automation
```

The script installs everything defined in `requirements.workspace.txt`, ensuring automation like `project-control-panel.sh` and docs MCP services never fail with `ModuleNotFoundError`.

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

## Model entrypoints

### LM Studio (local OpenAI-compatible server)

1. Launch LM Studio → **Local Server** tab → start the HTTP server (default `http://127.0.0.1:1234/v1`).
2. Verify the endpoint:

   ```bash
   curl http://127.0.0.1:1234/v1/models | jq '.data[].id'
   curl http://127.0.0.1:1234/v1/chat/completions \
     -H 'Content-Type: application/json' \
     -d '{"model":"deepseek/deepseek-r1-0528-qwen3-8b","messages":[{"role":"system","content":"You are a concise assistant."},{"role":"user","content":"State the workspace name."}]}'
   ```

3. `n00-cortex/data/llms.yaml` now ships the `litellm/lmstudio-deepseek` provider (air-gapped, pointing at the LM Studio server). Run planners or other tooling with:

   ```bash
   n00t plan docs/experiments/sample-brief.adoc \
     --model litellm/lmstudio-deepseek --airgapped --force
   ```

4. To keep telemetry consistent, set `LITELLM_BASE_URL=http://127.0.0.1:1234/v1` and `LITELLM_API_KEY=dummy` before invoking any scripts that load `litellm`.

### GitHub Models / Codex

_Preferred remote fallback when LM Studio/ollama are unavailable._

```bash
export GITHUB_TOKEN=<fine-grained token with "codespace" scope>
curl https://models.inference.ai.azure.com/chat/completions \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "model": "gpt-4.1-mini",
        "messages": [
          {"role":"system","content":"You are Codex, the workspace planner."},
          {"role":"user","content":"Summarise docs/modules/ROOT/pages/planning.adoc"}
        ]
      }'
```

Add a matching provider entry in `n00-cortex/data/llms.yaml` (transport `litellm`, `api_base: https://models.inference.ai.azure.com`, `airgapped: false`) when you want planners to target Codex/GitHub Models directly.

### GitHub Copilot / VS Code surface

1. Install the Copilot Chat + MCP Preview extensions in VS Code.
2. Point `.vscode/settings.json` at the same MCP servers described earlier (ai-workflow/cortex/n00-docs). Copilot will expose them as `/mcp` slash-commands.
3. Inside Copilot Chat run `/model gpt-4o-mini` (for hosted Codex) or `/model local` (once the VS Code Copilot agent supports LM Studio via OpenAI-compatible endpoints).
4. Use Copilot to orchestrate workspace entrypoints exactly like CLI agents: ask it to call `run_workflow_phase`, `n00t plan`, or to read docs via the MCP resources.

This combination keeps local LM Studio inference, GitHub-hosted Codex, and Copilot Chat aligned so the planned root application + editor tooling stay in lock-step.

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

## Planning + Typesense validation

1. **Planner invocation**

   ```bash
   n00t plan docs/experiments/sample-brief.md --airgapped --force
   ```

   - Verifies the new `workspace.plan` capability via `.dev/automation/scripts/plan-exec.sh`.
   - Produces `<brief>.plan.md` plus telemetry under `.dev/automation/artifacts/plans/`. Confirm DRY/YAGNI scores meet thresholds (see `docs/PLANNING.md`).

1. **Conflict gate**

   ```bash
   .dev/automation/scripts/plan-resolve-conflicts.py --telemetry .dev/automation/artifacts/plans/<file>.json --allow 0
   ```

   Ensures no unresolved `[[RESOLVE]]` anchors remain before PR merge.

1. **Typesense container smoke test**

   ```bash
   cp docs/search/docsearch.typesense.env.example docs/search/.env
   pnpm exec antora antora-playbook.yml
   npx http-server build/site -p 8080 & echo $! > docs/search/logs/http.pid
   docker compose -f docs/search/typesense-compose.yml up -d
   CONFIG=$(node -e "const fs=require('fs');const c=JSON.parse(fs.readFileSync('docsearch.config.json','utf8'));process.stdout.write(JSON.stringify(c));")
   docker run --rm --network host \
   -e CONFIG="$CONFIG" \
   -e TYPESENSE_API_KEY=$(grep TYPESENSE_API_KEY docs/search/.env | cut -d= -f2-) \
   -e TYPESENSE_HOST=127.0.0.1 \
   -e TYPESENSE_PORT=8108 \
   -e TYPESENSE_PROTOCOL=http \
   typesense/docsearch-scraper:0.9.0 | tee docs/search/logs/typesense-reindex-$(date +%Y%m%d).log
   node docs/search/scripts/save-typesense-summary.mjs docs/search/logs/typesense-reindex-$(date +%Y%m%d).log
   kill $(cat docs/search/logs/http.pid) && rm docs/search/logs/http.pid
   docker compose -f docs/search/typesense-compose.yml down
   ```

   Confirms the OSS search stack (Lunr + Typesense) works locally prior to CI. Archive the log under `docs/search/logs/` (latest: `typesense-reindex-20251119.log`) and its generated JSON summary so reviewers can verify record counts without rerunning the scraper. See `docs/modules/ROOT/pages/planning.adoc` and `docs/search/README.adoc` for details.

## Residual risks

- Capabilities that point outside this repo (one level up) require the super-root to exist locally; CI agents must mount `/Volumes/APFS Space/n00tropic/.dev/automation`. Fallback: override entrypoints via environment variables when running in isolated clones.
- Workflow scripts assume executable bits; rerun `chmod +x .dev/automation/scripts/ai-workflows/*.sh` if Git resets permissions.
- Keep `@modelcontextprotocol/sdk` aligned across servers to avoid protocol drift.

Following this runbook ensures agents can traverse every orchestration path (workspace health, project lifecycle, AI workflows, documentation references) using a consistent MCP interface.
