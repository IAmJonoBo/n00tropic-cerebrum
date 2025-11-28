# ADR-007: Proactivity Doctrine & Workspace Health Enforcement

## Status

Accepted – 2025-11-28

## Context

The federated workspace relies on ephemeral runners and agent-driven automation. Recent incidents showed:

- missing skeleton stubs and manifest entries for new repos caused health checks to pass locally but fail in CI;
- pnpm/Trunk binaries were absent on fresh runners, blocking lint + Antora builds;
- agents lacked a single entrypoint to remediate drift (skeleton apply, submodule sync, safe clean, branch ensure).

To keep downstream repos (`n00-frontiers`, `n00-cortex`, `n00t`, `n00tropic`) aligned, we need a doctrine that:

- makes “proactive repair” the default before any PR/automation run,
- gates new repos and gitmodules on manifest/skeleton presence,
- exposes the remediation path through n00t so humans and agents share the same lever.

## Decision

1. **Proactivity rule** – Every runner/agent must run the workspace repair flow (skeleton apply → submodule sync → safe clean → branch ensure) before plan/build/release tasks. Fail the run if remediation is skipped.
2. **Manifest gate** – Any new repo or gitmodule must be added to `automation/workspace.manifest.json` and have skeleton stubs present; CI blocks otherwise (`manifest-gate.sh` + workspace-health).
3. **Toolchain readiness** – Runners must bootstrap pnpm@10.23.x, Trunk CLI v1.25.x (external `TRUNK_BIN`), and `.venv-workspace` via `scripts/bootstrap-python.sh` prior to automation.
4. **Agent surface** – n00t ships a first-class capability that executes the repair flow in dry-run by default, with `apply=true` to persist fixes and publish `artifacts/workspace-health.json`.
5. **Docs & Start Here** – Root `START HERE` and repo start pages reference this doctrine so contributors know the required order: GH_SUBMODULE_TOKEN → `bootstrap-workspace.sh` → toolchains → repair → plan/build.

## Consequences

- Positive: Single, repeatable repair path reduces drift and CI noise; agents and humans share the same workflow.
- Positive: New repos cannot land without manifest + skeleton coverage, improving ecosystem observability.
- Neutral: Slightly longer bootstrap time on fresh runners; requires caching pnpm/Trunk binaries.
- Negative: Runs may fail early when credentials/cache directories are missing; must document local cache overrides (ANTORA_CACHE_DIR, TRUNK_CACHE_DIR) for sandboxed environments.

## Implementation Notes

- Capability: `workspace.repair` (n00t) targets `.dev/automation/scripts/workspace-health.py` with `autoRemediate` + `publishArtifact` flags; dry-run remains the default.
- Runner bootstrap order: `scripts/setup-pnpm.sh` → `ALLOW_ROOT_PNPM_INSTALL=1 pnpm install` → external Trunk binary (`TRUNK_BIN`) → `scripts/bootstrap-python.sh`.
- Cache overrides for sandboxed runners: set `ANTORA_CACHE_DIR` and `TRUNK_CACHE_DIR` inside the workspace to avoid writes to `$HOME`.
- CI gate: keep `manifest-gate.sh` and `workspace-health.py --auto-remediate --strict` in pre-merge checks.
