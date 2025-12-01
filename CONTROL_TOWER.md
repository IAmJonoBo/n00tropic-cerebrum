# ControlTower (Swift)

Workspace-local control CLI for the n00tropic superproject.

Build/Run:
```bash
cd /Volumes/APFS Space/n00tropic/n00tropic-cerebrum
swift run control-tower help
```

Commands:
- `status` – show detected workspace paths (package root, n00-cortex location).
- `validate-cortex` – run `pnpm run validate:schemas` inside `n00-cortex`.
- `graph-live` – rebuild catalog graph with live workspace inputs.
- `graph-stub` – rebuild graph using only in-repo assets (CI-safe).
- `sync-n00menon` – run `pnpm run docs:sync-n00menon --write` to pull doc updates into the workspace.

Notes:
- The binary assumes `n00-cortex` lives at `<workspace-root>/n00-cortex`.
- Commands stream stdout/stderr directly; non-zero exits are surfaced.
- pnpm 10.23.0 is invoked via `npx pnpm@10.23.0` for cortex validation.
- Edge scaffolds (RPi/Jetson) and agent guardrail routes land in this run; add tracing via `ai-mlstudio.tracing.open` before simulation.
- QA guardrail: keep coverage ≥85% across subrepos; for agent-core run `python -m pytest` (coverage) and `pnpm -C n00t run test` (Vitest) before orchestration sims.
- Observability: guardrail decisions (`guardrail.decision`, `guardrail.prompt_variant`) and router selections (`router.model_id`, `router.confidence`) are exported via `observability.py` / `observability-node.mjs`. Dashboards materialize to `artifacts/telemetry/edge-dashboard.json`.
- Script ergonomics: prefer `./bin/workspace <cmd>` (`health`, `meta-check`, `release-dry-run`, `deps-audit`, `ingest-frontiers`, `render-templates`) as the stable entrypoint; legacy scripts remain under `.dev/automation/scripts/`.
- Parallel runs: `meta-check.sh` and `sync-venvs.py` accept `--jobs N` (via `META_CHECK_JOBS`) for safe parallel venv sync and related steps; default remains serial for predictability.
