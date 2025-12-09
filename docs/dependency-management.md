# Dependency Management Stack

AGENT_HOOK: dependency-management

## Overview

- **Renovate**: canonical config lives at `renovate-presets/workspace.json` and is consumed by `renovate.json` plus all subrepo/template `renovate.json` files. Existing extend-check/apply workflows remain unchanged.
- **SBOMs via Syft**: `.dev/automation/scripts/deps-sbom.sh` reads `automation/workspace.manifest.json` targets and writes CycloneDX JSON to `artifacts/sbom/<target>/<ref>/`. GitHub Actions workflow `.github/workflows/sbom.yml` runs on `main` and tags.
- **Dependency-Track**: ops bundle under `ops/dependency-track/` (compose + project map). Upload script `.dev/automation/scripts/deps-dependency-track-upload.sh` pushes SBOMs when secrets are present.
- **Automation surfaces**: CLI (`cli.py`) commands `deps:sbom`, `deps:audit`, `deps:renovate:dry-run`; MCP capabilities will expose the same entrypoints for agents.
  - Drift detection: `deps:drift` (CLI/MCP) reports version mismatches and deprecated packages with recommended replacements.

## How to use (humans & agents)

- Generate SBOMs locally:
  ```bash
  ./cli.py deps:sbom               # all targets
  ./cli.py deps:sbom --target n00t --target n00-cortex --format spdx-json
  ./cli.py deps:sbom --list        # show available targets
  ```
- Check for drift/deprecations:
  ```bash
  ./cli.py deps:drift                          # table + json, writes artifacts/deps-drift/latest.json
  ./cli.py deps:drift --ignore husky --format json
  ```
- Generate + upload (requires Dependency-Track secrets):
  ```bash
  export DEPENDENCY_TRACK_BASE_URL=https://dtrack.example.com
  export DEPENDENCY_TRACK_API_KEY=xxxx
  ./cli.py deps:audit --target n00tropic
  ./cli.py deps:audit --skip-upload   # SBOM only, no upload
  ```
- Renovate dry-run (local, no PRs):
  ```bash
  ./cli.py deps:renovate:dry-run
  ./cli.py deps:renovate:dry-run --log-level debug
  ```
- Self-hosted (no GitHub secrets) upload:
  ```bash
  # On the SSH-accessible host where Dependency-Track runs
  cp ops/dependency-track/.env.example ops/dependency-track/.env
  # fill DT_ADMIN_PASSWORD, DT_BASE_URL, DEPENDENCY_TRACK_API_KEY locally
  ./cli.py deps:audit --target workspace
  ```
  CI remains non-blocking; it will warn if uploads are skipped.

### Local env helpers (keep off GitHub)

- Copy `env/dependency-management.env.example` to `env/dependency-management.env` on your SSH host and fill values for Dependency-Track, Typesense, optional PATs, and webhooks. Source it before running CLI commands if you want defaults:
  ```bash
  set -a && source env/dependency-management.env && set +a
  ./cli.py deps:audit --target workspace
  ```

## Dependency-Track end-to-end setup (self-hosted)

1. Start services

   ```bash
   cp ops/dependency-track/.env.example ops/dependency-track/.env
   # edit: DT_ADMIN_PASSWORD (strong), DT_BASE_URL (e.g., http://localhost:8081)
   docker compose -f ops/dependency-track/docker-compose.yml up -d
   ```

   - API: `http://localhost:8081`
   - UI: `http://localhost:8080`

2. Create an API key (UI)
   - Open the UI on port 8080, log in with `admin` / `DT_ADMIN_PASSWORD`.
   - Go to **Administration → Access Management → Teams → Administrators → API Keys** (tab on the right) and generate a key.
   - Add it to `ops/dependency-track/.env` as `DEPENDENCY_TRACK_API_KEY` (quote if it contains `!`; keep file local/off-GitHub).

3. Install Syft locally (once per host)

   ```bash
   mkdir -p bin
   curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b ./bin
   export PATH="$PWD/bin:$PATH"
   ```

4. Run SBOM + upload from the host

   ```bash
   set -a && source ops/dependency-track/.env && set +a
   export PATH="$PWD/bin:$PATH"
   ./cli.py deps:audit --target workspace   # generates SBOMs and uploads to DT
   ```

   - If `DEPENDENCY_TRACK_BASE_URL` or `DEPENDENCY_TRACK_API_KEY` are unset, the upload step is skipped with a warning but the SBOM is still produced.

5. Troubleshooting
   - If Syft missing: ensure `PATH` includes `./bin` or install via Homebrew/Linux install script.
   - If UI shows only swagger: you’re on 8081 (API). Use 8080 for the full UI.
   - Syft warnings about yarn `__metadata` are benign; SBOM still produced. Set `SYFT_YARN_ENABLE_EXPERIMENTAL_PARSER=true` to reduce noise (already defaulted in scripts/env).
   - To make drift checks gate CI, run `deps-drift.py --fail-on any` (or `major`). Plan output is at `artifacts/deps-drift/plan.json`.

### Secrets / tokens to provision (scoped, PAT preferred over repo token when possible)

- `GH_TOKEN` (PAT, repo-only scope) — avoids rate limits for runner health + general automation; workflows fall back to `GITHUB_TOKEN` if absent.
- `DISCORD_WEBHOOK` — optional notifications used by runners-nightly and python-lock-check.
- Typesense (search-reindex): `TYPESENSE_API_KEY`, `TYPESENSE_PROTOCOL`, `TYPESENSE_HOST`, `TYPESENSE_PORT`, `TYPESENSE_COLLECTION` — set once at repo/org scope to avoid per-branch drift.
- `TRUNK_SYNC_PAT` — minimal repo-scope PAT for trunk-sync automation.
- `REQUIRED_RUNNER_LABELS` — string to override default runner label checks (can be secret or variable).

Prefer storing these in your SSH host `.env` (or env vars for the runner) if you want to keep GitHub secret usage minimal; the workflows remain warning-only when absent.

## CI behaviour

- Workflow: `.github/workflows/sbom.yml`
  - Matrix over manifest targets.
  - Installs Syft, runs `deps-sbom.sh`, uploads artefacts, then calls `deps-dependency-track-upload.sh` when `DEPENDENCY_TRACK_BASE_URL` and `DEPENDENCY_TRACK_API_KEY` are configured.
- Outputs: SBOMs and upload responses are stored under `artifacts/sbom/<target>/<ref>/` per job.

## Dependency-Track notes

- Ops bundle: `ops/dependency-track/docker-compose.yml` + `ops/dependency-track/README.md` (local quickstart + env hints).
- Project naming: `ops/dependency-track/projects.json` maps targets to `n00tropic-cerebrum::<target>` identifiers; upload script uses this mapping.
- Required secrets for uploads: `DEPENDENCY_TRACK_BASE_URL`, `DEPENDENCY_TRACK_API_KEY` (BOM upload scope). Set these in GitHub repo secrets for CI.

## Renovate configuration

- Central preset: `renovate-presets/workspace.json` (labels, schedules, ecosystem coverage). Root config `renovate.json` adds surfacing rules for esbuild/storybook/vitest/tsup majors.
- Subrepos/templates already extend the central preset via `github>n00tropic/n00tropic-cerebrum//renovate-presets/workspace.json` or `local>renovate-presets/workspace.json`.
- Local preview: `./cli.py deps:renovate:dry-run` uses `--platform=local` so no GitHub token is required.

## File map (for agents)

- `renovate-presets/workspace.json` – central Renovate preset (AGENT_HOOK).
- `.dev/automation/scripts/deps-sbom.sh` – Syft SBOM generator (AGENT_HOOK).
- `.dev/automation/scripts/deps-audit.sh` – SBOM + Dependency-Track upload orchestrator (AGENT_HOOK).
- `.dev/automation/scripts/deps-dependency-track-upload.sh` – raw upload helper (AGENT_HOOK).
- `.dev/automation/scripts/deps-renovate-dry-run.sh` – Renovate dry-run helper (AGENT_HOOK).
- `.dev/automation/scripts/deps-drift.py` – drift + deprecation detector (AGENT_HOOK).
- `.github/workflows/deps-drift.yml` – CI drift report uploader (non-blocking).
- `.github/workflows/sbom.yml` – SBOM generation; uploads are warning-only when secrets are absent (use local .env instead).
- Drift CI now runs with `--fail-on any`, so keep versions aligned to stay green; see `artifacts/deps-drift/plan.json` for the bump plan.
- `.github/workflows/trunk-upgrade-recursive.yml` – weekly Trunk plugin upgrade across all repos (auto-inits missing `.trunk/trunk.yaml`), pushes changes automatically.

## Lint visibility & guardrails

- Trunk is the single entrypoint; each repo keeps its own `.trunk/trunk.yaml`. The upgrade workflow runs in every repo to respect per-language settings.
- For “live” feedback locally: run `trunk check --watch` or `trunk check --changed --no-fix` to mirror IDE Problems.
- To auto-init new repos: `TRUNK_INIT_MISSING=1 .dev/automation/scripts/trunk-upgrade.sh` (used in CI) will run `trunk init --ci --no-progress` only when a repo lacks Trunk config, avoiding overwrites of existing configs.
- MCP lint hook: capability `deps.trunkLint` runs `trunk check` (default `--changed`) and returns the log path under `artifacts/trunk/`. Inputs: `scope` (`changed`|`all`), optional `filter`.

## Lint visibility & guardrails

- Trunk is the single entrypoint; each repo keeps its own `.trunk/trunk.yaml`. The upgrade workflow runs in every repo to respect per-language settings.
- For “live” feedback locally: run `trunk check --watch` or `trunk check --changed --no-fix` to mirror IDE Problems.
- To auto-init new repos: `TRUNK_INIT_MISSING=1 .dev/automation/scripts/trunk-upgrade.sh` (used in CI) will run `trunk init --ci --no-progress` only when a repo lacks Trunk config, avoiding overwrites of existing configs.
- `.github/workflows/sbom.yml` – CI SBOM + upload workflow (AGENT_HOOK).
- `ops/dependency-track/docker-compose.yml`, `ops/dependency-track/README.md`, `ops/dependency-track/projects.json` – Dependency-Track deployment + mapping (AGENT_HOOK).
