# n00man Evaluation Plan

> Scope: MCP-facing automation for `n00man.scaffold`, `n00man.validate`, and `n00man.list`, plus the underlying governance engine.

## Objectives & Metrics

| Metric                 | Description                                                                                                       | Target                                          | Collection                                                                                                                                                      |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Governance compliance  | Every profile (registry + ad-hoc payloads) must satisfy schema + roles + guardrails validation.                   | 100% pass rate                                  | `python -m pytest n00man/tests` + `.dev/automation/scripts/n00man/n00man-validate.py --agent-id <id>`                                                           |
| Registry introspection | Listing/filtering must return structured data for all agents without mutation.                                    | Stable JSON payload, `count == len(agents)`     | `.dev/automation/scripts/n00man/n00man-list.py [--filters]`                                                                                                     |
| Scaffolding fidelity   | Scaffolding should emit registry & doc artefacts and respect guardrails. Exercise via sandbox registry/doc roots. | Zero governance errors, generated files tracked | `.dev/automation/scripts/n00man/scaffold-smoke.py --keep-sandbox` (wraps `n00man-scaffold.py --docs-root <tmp>/docs --registry-path <tmp>/agent-registry.json`) |
| Telemetry hooks        | Trace spans propagated for MCP executions (OTLP).                                                                 | Span emitted per scaffold run                   | `n00man.scaffold` via MCP with tracing endpoint configured                                                                                                      |

## Test Inputs

1. **Golden registry sample**: `n00man/docs/agent-registry.json` (contains `n00veau`). Used for validate/list baselines.
2. **Synthetic agent briefs**: `n00man/docs/briefs/*.json` currently tracks analyst/integrator/reviewer/operator/assistant exemplars (Aegis, Relay, Solstice, Keystone, Pulse, Atlas) for sandbox + governance sims.
3. **Guardrail bundles**: YAML/JSON describing escalation policies + safety rails (converted to JSON for automation input).
4. **Failure fixtures**: intentionally malformed payloads (missing role, invalid guardrail) to assert negative paths.

## Simulation Matrix

| Simulation           | Purpose                                                                       | Steps                                                                                                                              |
| -------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Registry smoke       | Ensure read-only listing works everywhere.                                    | Run `.dev/automation/scripts/n00man/n00man-list.py --registry-path <path>` and assert `count`                                      |
| Governance sweep     | Validate every registry entry + synthetic payloads.                           | `.dev/automation/scripts/n00man/governance-sweep.py` (loads `docs/briefs/*.json`, writes artifact summaries)                       |
| Sandbox scaffold     | Verify scaffolding writes only within sandbox.                                | `.dev/automation/scripts/n00man/scaffold-smoke.py --keep-sandbox` (uses new `--docs-root/--registry-path` overrides)               |
| MCP capability smoke | Exercise MCP wiring via `n00t` to ensure outputs/telemetry match manifest.    | Invoke `n00man.scaffold`, `n00man.validate`, and `n00man.list` from `n00t/capabilities/manifest.json` using the capability runner. |
| MCP end-to-end       | Trigger full agent creation/validation/list flows against a sandbox registry. | Chain MCP capability calls with `docsRoot` overrides so generated artefacts stay inside automation sandboxes.                      |

## Tooling & Automation

- **Unit tests**: `python -m pytest n00man/tests` remains the fast governance signal.
- **Automation scripts**: `scaffold-smoke.py` and `governance-sweep.py` persist run metadata in `.dev/automation/artifacts/n00man/`; integrate them into `workspace.metaCheck` alongside MCP smokes.
- **MCP surface**: `n00t/capabilities/manifest.json` now exposes `n00man.scaffold`, `n00man.validate`, and `n00man.list`, all pointing at the automation scripts with tracing enabled so OTLP spans carry `agent.id` attributes.
- **Tracing**: ensure OTLP endpoint from `n00t/capabilities/manifest.json` is reachable; confirm spans include `agent.id` attributes.

## Next Steps

1. Automate `scaffold-smoke.py` + `governance-sweep.py` via CI/metaCheck and surface artefact paths in build logs.
2. Capture MCP smoke results (for `n00man.scaffold/validate/list`) as `.dev/automation/artifacts/n00man/mcp-*.json` so telemetry parity is auditable.
3. Add evaluation CI job that runs list + validate sims on every registry change (can invoke `governance-sweep.py`).
4. Feed the briefs dataset through the MCP flows regularly and confirm OTLP spans propagate `agent.id` + sandbox registry paths.

## Sandbox Usage Notes

- Use `--docs-root` and `--registry-path` when calling `.dev/automation/scripts/n00man/n00man-scaffold.py` directly to keep writes inside a scratch directory.
- `.dev/automation/scripts/n00man/scaffold-smoke.py` wraps the scaffold command, copies `n00man/docs` into a temp sandbox, and verifies output paths stay within that sandbox. Pass additional scaffold flags after `--`.
