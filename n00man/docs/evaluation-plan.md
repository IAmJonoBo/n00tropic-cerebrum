# n00man Evaluation Plan

> Scope: MCP-facing automation for `n00man.scaffold`, `n00man.validate`, and `n00man.list`, plus the underlying governance engine.

## Objectives & Metrics

| Metric                 | Description                                                                                                       | Target                                          | Collection                                                                                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Governance compliance  | Every profile (registry + ad-hoc payloads) must satisfy schema + roles + guardrails validation.                   | 100% pass rate                                  | `python -m pytest n00man/tests` + `.dev/automation/scripts/n00man/n00man-validate.py --agent-id <id>`                                                     |
| Registry introspection | Listing/filtering must return structured data for all agents without mutation.                                    | Stable JSON payload, `count == len(agents)`     | `.dev/automation/scripts/n00man/n00man-list.py [--filters]`                                                                                               |
| Scaffolding fidelity   | Scaffolding should emit registry & doc artefacts and respect guardrails. Exercise via sandbox registry/doc roots. | Zero governance errors, generated files tracked | `.dev/automation/scripts/n00man/n00man-scaffold.py --agent-id demo --registry-path <tmp>/registry.json --docs-root <tmp>/docs` (future flag) + diff check |
| Telemetry hooks        | Trace spans propagated for MCP executions (OTLP).                                                                 | Span emitted per scaffold run                   | `n00man.scaffold` via MCP with tracing endpoint configured                                                                                                |

## Test Inputs

1. **Golden registry sample**: `n00man/docs/agent-registry.json` (contains `n00veau`). Used for validate/list baselines.
2. **Synthetic agent briefs**: author one JSON payload per agent role (reviewer, researcher, integrator).
3. **Guardrail bundles**: YAML/JSON describing escalation policies + safety rails (converted to JSON for automation input).
4. **Failure fixtures**: intentionally malformed payloads (missing role, invalid guardrail) to assert negative paths.

## Simulation Matrix

| Simulation       | Purpose                                                                             | Steps                                                                                                           |
| ---------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Registry smoke   | Ensure read-only listing works everywhere.                                          | Run `.dev/automation/scripts/n00man/n00man-list.py --registry-path <path>` and assert `count`                   |
| Governance sweep | Validate every registry entry + synthetic payloads.                                 | `for agent in registry: n00man-validate --agent-id agent` plus `--profile-path` for payloads                    |
| Sandbox scaffold | Verify scaffolding writes only within sandbox.                                      | Copy `n00man/docs` to `/tmp/n00man-lab`, run scaffold with future `--registry-path`/`--docs-root`, diff outputs |
| MCP end-to-end   | Exercise capabilities via MCP runner to ensure guardrails + outputs match manifest. | Trigger `n00man.scaffold/validate/list` through `n00t` capability runner once published                         |

## Tooling & Automation

- **Unit tests**: `python -m pytest n00man/tests` remains the fast governance signal.
- **Automation scripts**: integrate into `workspace.metaCheck` once MCP capabilities stabilize.
- **Tracing**: ensure OTLP endpoint from `n00t/capabilities/manifest.json` is reachable; confirm spans include `agent.id` attributes.
- **Future work**: add optional `--docs-root` and `--registry-path` overrides to `n00man-scaffold.py` for side-effect-free sims.

## Next Steps

1. Implement scaffold sandbox flags + smoke harness.
2. Wire MCP runners to capture artifacts into `.dev/automation/artifacts/n00man/` for history.
3. Add evaluation CI job that runs list + validate sims on every registry change.
4. Expand dataset with at least three additional agent briefs before beta launch.
