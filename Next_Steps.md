# Next Steps

## Tasks

- [x] Authenticate and sync required submodules (owner: codex, completed: 2025-11-20; see Next_Steps_Log)
- [x] Add CODEOWNERS coverage for workspace root paths touched in this change (owner: codex, completed: 2025-11-20)
- [ ] Restore pnpm toolchain + external Trunk binary (owner: codex, due: 2025-02-05)
  - Run `scripts/setup-pnpm.sh` (corepack prepare pnpm@10.23.0; npm global fallback added) and `pnpm install` at workspace root.
  - Install trunk CLI v1.25.4 to `~/.cache/trunk/bin/trunk` (or another runner-level location) and export `TRUNK_BIN`; the workspace no longer ships `.trunk/trunk.yaml`, so runners must source lint configs from `n00-cortex/data/trunk/base/.trunk/` or downstream repos directly.
  - Trunk defs sync script restored at `scripts/sync-trunk-defs.mjs`; invoked automatically by `.dev/automation/scripts/run-trunk-subrepos.sh` against the canonical configs under `n00-cortex/data/trunk/base/.trunk/`.
- [x] Repair Biome script lint path (owner: codex)
  - After pnpm is present, re-run `pnpm -w exec biome check scripts` (avoid quoting the glob) to validate scripts linting.
- [x] Remediate OSV scanner alerts for `mcp` (GHSA-3qhf-m339-9g5v, GHSA-j975-95f5-7wqh) (owner: codex)
  - Dependency bumped to `mcp>=1.10.0` in `mcp/docs_server/requirements.txt`; rerun `osv-scanner` to verify closure.
- [x] Restore superrepo health artifact (owner: codex)
  - Clean local-only submodule changes (`n00-horizons` untracked jobs, `n00t` tracked `capabilities/manifest.json`), then rerun `.dev/automation/scripts/workspace-health.py --publish-artifact`.
- [x] Proactive skeleton auto-apply + manifest backfill (owner: codex, completed: 2025-11-24)
  - `check-workspace-skeleton.py --apply` scaffolds required dirs/stubs and backfills manifest entries; reports created stubs.
- [x] Workspace health auto-remediate & fix-plan output (owner: codex, completed: 2025-11-24)
  - `workspace-health.py --auto-remediate` runs skeleton apply, submodule sync, safe clean, branch ensure, and emits fix plan.
- [x] Manifest gate for new repos/gitmodules (owner: codex, completed: 2025-11-24)
  - `manifest-gate.sh` + CI step block missing manifest entries.
- [x] Bootstrap new-repo scaffolder (owner: codex, completed: 2025-11-24)
  - `scripts/bootstrap-repo.sh --name <repo> --role <role>` scaffolds and appends manifest entry.
- [x] Mirror manifest/skeleton checks in key subrepos (owner: codex, completed: 2025-11-29)
  - Thin wrappers added in `n00-frontiers/scripts/workspace-skeleton.sh`, `n00-cortex/scripts/workspace-skeleton.sh`, and `n00t/scripts/workspace-skeleton.sh` to run root checks when used standalone.
- [x] Proactivity doctrine ADR + docs (owner: docs, completed: 2025-11-28)
  - Add ADR in `1. Cerebrum Docs` and update root/START HERE with the proactivity + manifest requirements.
- [x] n00t capability for repair/apply (owner: automation/agent platform, completed: 2025-11-28)
  - Expose skeleton apply + health auto-remediate via n00t capability manifest (dry-run by default).
- [ ] Repair workspace health sync for ephemeral agents (owner: codex)
  - Document bootstrap order for runners: `GH_SUBMODULE_TOKEN` → `scripts/bootstrap-workspace.sh` → `pnpm install` → `scripts/bootstrap-python.sh` → `pnpm exec antora antora-playbook.yml` (skip if private sources unavailable).
- [ ] Fix Python bootstrap notes (owner: codex)
  - Confirm `requirements.workspace.txt` resolves now that submodules exist; keep guidance to activate `.venv-workspace` before running automation.
- [ ] Repair Antora docs build (owner: codex)
  - After pnpm/trunk restore, run `pnpm exec antora antora-playbook.yml --stacktrace`; validate playbook paths for doc branches.
- [ ] Harden MCP servers/prompts/tracing for agent parity (owner: automation/agent platform)
  - Run MCP services from `.venv-workspace`, keep prompt manifests in sync with docs, and ensure OTEL env (`OTEL_EXPORTER_OTLP_ENDPOINT`, `N00_DISABLE_TRACING`) is set before launching ai-workflow/cortex/docs servers.
- [ ] Schedule planner telemetry exports + Typesense freshness guards + dashboard updates (owner: horizons/school PMs)
  - Export `.dev/automation/artifacts/plans/horizons-*.json` into dashboards, refresh `docs/search/logs/typesense-reindex-*.log[.json]` (<7d), and publish planner-GA runs per `docs/modules/ROOT/pages/closing-gaps.adoc`.

## Steps

1. Bootstrap toolchain (pnpm via corepack; trunk CLI install; python venv via `scripts/bootstrap-python.sh`).
2. Sync submodules and artifacts (`scripts/check-superrepo.sh`, `.dev/automation/scripts/workspace-health.py --sync-submodules --publish-artifact`).
3. Restore linters/formatters (`pnpm -w exec biome check scripts`, `.dev/automation/scripts/run-trunk-subrepos.sh --fmt` once the external `TRUNK_BIN` is available).
4. Rebuild docs and search (`pnpm exec antora antora-playbook.yml`; rerun `docsearch.config.json` workflow if search is enabled).
5. Run security + health (`osv-scanner --config osv-scanner.toml .`, confirm GHSA items cleared).
6. Mirror Antora/Vale/Lychee + Markdown→AsciiDoc migrations across repos listed in `docs/modules/ROOT/pages/migration-status.adoc` when private submodules are reachable.

### Pipeline validation

- `scripts/validate-pipelines.sh --clean` creates temp fixtures, runs preflight → graph export → docs build → fusion (if venv present), and writes logs to `.dev/automation/artifacts/pipeline-validation/latest.json`.
- Validator defaults to the local playbook (`antora-playbook.local.yml`) to avoid remote creds; set `ANTORA_PLAYBOOK=antora-playbook.ci.yml` if you want remote fetch. Provide `GH_SUBMODULE_TOKEN` when hitting private sources.

### Local runners, creds, and CLIs (use local first)

- Each repo has its own environment; prefer running pipelines locally (superproject scripts under `scripts/`, subrepo helpers under their `scripts/` or `.dev/automation/scripts/` folders) before relying on remote runners.
- For private fetches (Antora, submodules), set `GH_SUBMODULE_TOKEN` in your shell; validator auto-wires it via a temporary `git-askpass` if present.
- When credentials are unavailable, fall back to local artifacts and CLIs: run `scripts/validate-pipelines.sh --skip docs` (or `--only graph`) to keep other checks green while you sort access.
- Keep local actions runners/CLIs installed so dev flows stay unblocked; during dev, aim to resolve with local execution first, then remote once credentials are restored/rotated.

## Deliverables

- Restored pnpm toolchain with default pnpm store location and documented external Trunk management.
- Regenerated `artifacts/workspace-health.json`.
- Passing trunk + Biome checks and Antora build.
- OSV scanner clean for `mcp/docs_server`.
- Updated migration status and runner bootstrap notes for agents.

## Quality Gates

- tests: pass
- linters/formatters: clean
- type-checks: clean
- security scan: clean
- coverage: ≥ baseline
- build: success
- docs updated

## Links

- Submodule/migration tracker: `docs/modules/ROOT/pages/migration-status.adoc`
- Antora migration playbook: `stuff/Temp/temp-doc-2.md`
- Trunk runner: `.dev/automation/scripts/run-trunk-subrepos.sh`
- Workspace health: `.dev/automation/scripts/workspace-health.py`
- Security fix: `mcp/docs_server/requirements.txt`
- Antora playbook: `antora-playbook.yml`

## Risks/Notes

- pnpm toolchain missing on current runner; install via `scripts/setup-pnpm.sh`. Trunk CLI must be installed outside this repo (launcher install script still 404—reuse cached binary or fetch the pinned GitHub release and set `TRUNK_BIN`).
- `n00-horizons` and `n00t` submodules carry local changes; clean or commit before rerunning workspace-health to avoid false positives.
- Antora build and docs migration depend on private submodules being readable (set `GH_SUBMODULE_TOKEN` for ephemeral agents).
