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

## Trunk Failure Taxonomy (Dec 2025)

| Bucket                    | Linter(s)                             | Hotspots                                                                                             | Primary Owner                             | Notes                                                                                                                                              |
| ------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Security & Compliance** | Checkov (Docker/OpenAPI), osv-scanner | `stuff/frontier-webapp-template`, `stuff/n00tropic Handover Kit`, `stuff/n00tropic Library Template` | Template maintainers (Frontiers guild)    | Add HEALTHCHECK + non-root users to Dockerfiles, security blocks to OpenAPI/AsyncAPI specs, upgrade vulnerable deps or add annotated suppressions. |
| **Code Hygiene**          | Bandit, isort, trunk fmt              | `tests/test_mcp_suite.py`, `.dev/automation/scripts/**/*.py`                                         | Workspace tooling team                    | Replace `assert` with `self.assert*`, guard subprocess use, keep formatting clean post-automation.                                                 |
| **Docs & Style**          | Vale, markdownlint                    | `stuff/**/docs`, `.github/templates`, `docs/ai/**`                                                   | Docs & Enablement (n00menon)              | Convert headings to sentence case, remove trailing punctuation, avoid first-person plural, replace bare URLs with Markdown links.                  |
| **Style Definitions**     | yamllint                              | `styles/Google/*.yml`, `styles/Microsoft/*.yml`, `styles/n00/*.yml`                                  | Docs tooling                              | Remove redundant quoting and ensure lint configs parse cleanly.                                                                                    |
| **Template Fingerprints** | Custom verification (n00-frontiers)   | `n00-frontiers/templates/_fingerprints/**` per template                                              | Respective subrepos (grace period active) | Every template/context needs a committed fingerprint; warnings in CI now, will flip to blocking once all subrepos adopt the workflow.              |

Keep this table updated as categories clear; when a bucket hits zero findings, annotate the date and owner sign-off here before relaxing any suppressions.
