# n00tropic Cerebrum workspace

The Cerebrum workspace stitches together the repositories that power n00tropic's platform: changelog automation, documentation, agent workflows, training curricula, and template generators. Each repository keeps its own release cadence and tooling, while this workspace supplies shared automation and alignment.

## Ecosystem map

```mermaid
graph TD
Cortex["n00-cortex\nSchemas & Docs"] --> Frontiers["n00-frontiers\nTemplates, CLI, Renderers"]
Cortex --> N00t["n00t\nAgent & MCP Surface"]
N00t --> Frontiers
Frontiers --> N00plicate["n00plicate\nPolyglot Consumer"]
Frontiers --> Docs["1. Cerebrum Docs\nCross-repo ADRs"]
N00tropic["n00tropic\nOperational Playbooks"] --> Docs
N00school["n00-school\nTraining Curriculum"] --> N00t
N00school --> Frontiers
Frontiers --> Cortex
```

Schemas published from `n00-cortex` drive automation in `n00-frontiers`, which then feeds downstream consumers such as `n00plicate` and the shared documentation set. `n00t` orchestrates the automation surface, while doctrine (`n00tropic`) and training signals (`n00-school`) complete the feedback loop.

> Looking for the people-facing handbook? It now lives alongside the filesystem in `../n00tropic_HQ/`.

## Repository profiles

### `1. Cerebrum Docs/`

- **Focus**: cross-repo decision records, release manifests, and workspace onboarding docs.
- **Key artifacts**: ADRs, `RENOVATE_SETUP.md`, `TRUNK_GUIDE.md`, `releases.yaml` (written by automation).
- **Role**: canonical reference material other repos reference for shared policy.

### `n00-frontiers/`

- **Mandate**: authoritative source for software, delivery, and design excellence. Defines the standards that every downstream system follows.
- **Output**: templates, notebooks, CLI tooling, and the quality bar for frontier-grade work.
- **Cadence**: updated frequently; every change should be reflected in `docs/`, `catalog.json`, and TASKS/ADR tracking.

### `n00-cortex/`

- **Mandate**: systematizes and enforces the rules issued by `n00-frontiers`. Publishes schemas, manifests, and documentation that downstream consumers must obey.
- **Output**: JSON Schemas, toolchain manifests, canonical documentation site, and reusable templates.
- **Dependency**: pulls rendered assets and policies from `n00-frontiers` before distributing them.

### `n00tropic/`

- **Mandate**: organizational handbook and flagship generation engine. Houses briefs, discovery artifacts, and generators that translate context into scaffolded projects and assets.
- **Output**: context ingestion, directory/project scaffolding, and operational doctrine for every service pillar.
- **Integration**: feeds `n00t` with briefs and configuration; ensures generated artifacts comply with `n00-frontiers` and `n00-cortex`.

### `n00t/`

- **Mandate**: agent and automation control center. Discovers capabilities, runs workspace scripts, and brokers context between humans, agents, and repos.
- **Output**: MCP host, capability manifest, orchestration UI/CLI.
- **Integration**: invokes automation scripts and propagates telemetry back to `n00-cortex` and `n00-frontiers`.

### `n00plicate/`

- **Mandate**: platform-agnostic design asset + CDN generator. Converts Penpot/token sources into multi-runtime packages.
- **Output**: token orchestrator, UI kernel, framework adapters, and reference apps.
- **Integration**: aligns with `n00-frontiers` design rules and feeds packaged assets to `n00tropic` deliverables.

### `n00-school/`

- **Mandate**: training center and R&D lab for n00tropic assistants. Develops and evaluates pipelines that improve automation quality.
- **Output**: training datasets, pipelines, evaluation harnesses, and telemetry.
- **Integration**: capabilities surface through `n00t`; insights loop back into `n00-frontiers` standards.

### `n00-horizons/`

- **Mandate**: project management, ideation, and strategy hub. Ensures every idea is traceable to deliverables and upstream/downstream impacts.
- **Output**: experiment briefs, GitHub issue/project orchestration, and strategic playbooks.
- **Integration**: operates under the `n00-frontiers` horizon workflow and reports impacts to affected repos.

### `n00clear-fusion/`

- **Mandate**: ingestion, enrichment, and RAG-friendly export pipelines that transform PDFs, Word docs, tabular data, and transcripts into n00t-ready training packs.
- **Output**: `corpora/` manifests, `pipelines/` processors, and `exports/` bundles that downstream repos (n00-horizons jobs, n00-frontiers templates, n00t capabilities) can consume without extra glue code.
- **Integration**: shares derived assets with `n00-cortex` taxonomies, feeds cookiecutters/templates in `n00-frontiers`, and backfills `n00t` capabilities so agents can scaffold projects from curated source material.

## Cross-repo release flow

```mermaid
sequenceDiagram
participant Dev as Contributor
participant Cortex as n00-cortex
participant Frontiers as n00-frontiers
participant Docs as 1. Cerebrum Docs
participant Automation as .dev/automation

Dev->>Cortex: Update schemas and manifests
Cortex-->>Frontiers: Publish new toolchain rules
Dev->>Frontiers: Regenerate templates and run sanity checks
Dev->>Automation: Run meta-check and trunk sync
Automation-->>Docs: Write releases.yaml via workspace-release.sh
Docs-->>Dev: Document decisions and ADR updates
```

This sequence highlights the typical cadence: adjust policy in `n00-cortex`, adapt generators in `n00-frontiers`, validate via automation, and record the outcome in shared documentation.

## Automation toolkit

Automation scripts live under `.dev/automation/scripts/` and surface through the `n00t` capability manifest.

| Script                            | Purpose                                                                                                                                       |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `meta-check.sh`                   | Orchestrates repo health checks, schema validation, and CVE scans before publishing changes.                                                  |
| `refresh-workspace.sh`            | Fast-forwards each repo and updates submodules to keep local clones aligned.                                                                  |
| `trunk-upgrade.sh`                | Runs `trunk upgrade` across repos (supports repo filters and extra flags when invoked via capabilities).                                      |
| `check-cross-repo-consistency.py` | Ensures toolchain manifests and overrides remain aligned.                                                                                     |
| `workspace-release.sh`            | Verifies clean git state and writes `1. Cerebrum Docs/releases.yaml`.                                                                         |
| `ai-workflows/*`                  | Phase-specific scripts for the AI-assisted development workflow surfaced by `n00t`.                                                           |
| `project-preflight.sh`            | Chains capture + GitHub/ERPNext syncs and fails fast when review cadence, links, or IDs are missing.                                          |
| `project-lifecycle-radar.sh`      | Emits a JSON radar summarizing lifecycle totals, overdue reviews, and integration gaps for planning.                                          |
| `project-control-panel.sh`        | Builds `n00-horizons/docs/control-panel.md` so planning decks link runbooks, radar output, and preflights.                                    |
| `scripts/erpnext-run.sh`          | Run-and-gun ERPNext dev stack: bootstraps bench, verifies MySQL/Redis, launches browser, logs telemetry, and triggers PM/telemetry exports.   |
| `project-preflight-batch.sh`      | Executes preflight across every registry entry to keep GitHub + ERPNext sync warnings visible.                                                |
| `workspace-health.py`             | Summarizes root + submodule git status, emits `artifacts/workspace-health.json`, cleans safe untracked files, and syncs submodules on demand. |

Run `python cli.py --help` from the workspace root (or `n00-horizons/cli.py`, `n00-frontiers/cli.py`, etc.) to access curated wrappers around these scripts for both agents and humans.

Automation executions append telemetry to `.dev/automation/artifacts/automation/agent-runs.json`, which powers dashboards and agent insights.

## Subrepo contract and boundaries

- **Canonical remotes**: Every subrepo listed in `.gitmodules` maps to `https://github.com/n00tropic/<name>.git`. During cloning, run `git submodule update --init --recursive` (or `python cli.py workspace-health --sync-submodules`) so local remotes match the organization defaults.
- **Standalone readiness**: Each subrepo must boot with `pnpm install`, `pip install -r requirements.txt`, or its documented workflow without relying on files from other repos. Cross-repo assets move through published schemas (`n00-cortex`), catalogs (`n00-frontiers`), and generated bundles (`n00plicate`), never via direct relative imports.
- **Branch invariants**: `main` (or `doc` where noted) in every subrepo stays releasable. Feature branches may live either inside the subrepo or the superrepo, but merges always occur within the subrepo first so submodule pointers simply fast-forward.
- **Change propagation**: Update order stays Cortex -> Frontiers -> Consumers. When schema or template changes occur, tag the owning subrepo, then bump the submodule pointer in `n00tropic-cerebrum` via a workspace commit. Avoid editing generated assets under `n00-cortex/data/exports/**`, `n00-frontiers/applications/scaffolder/**`, or `n00tropic/06-Shared-Tools/Generated/`; rerun the documented generators instead.
- **Automation interface**: `n00t` surfaces capabilities from `.dev/automation/scripts/*`. When adding new automation, update `n00t/capabilities/manifest.json` and ensure logs land in `.dev/automation/artifacts/automation/` so subrepos can operate independently yet expose common tooling through the superrepo.

### Boundary enforcement checklist

1. Run `.dev/automation/scripts/workspace-health.sh --sync-submodules --json` (or `python cli.py workspace-health --sync-submodules`) to pin every submodule to its remote default and record git state in `artifacts/workspace-health.json`.
1. Execute `pnpm run trunk:check-all` so each repo proves formatter, lint, and unit-test parity before touching shared assets.
1. Inspect `git diff --submodule=log` to confirm only the intended submodules advanced and that the root repo contains the pointer bumps plus any automation/log artifacts.
1. Capture design or schema decisions in `1. Cerebrum Docs/ADR/` and link to the owning repo's ADR or TASK entry before merging cross-repo changes.
1. Release in the Cortex -> Frontiers -> Consumer order. Tag each repo before moving the next pointer so downstream repos consume only immutable versions.

### Interaction matrix

| Repo               | Owns                                     | Consumes                                      | Gate                                                 |
| ------------------ | ---------------------------------------- | --------------------------------------------- | ---------------------------------------------------- |
| `n00-cortex`       | Schemas, manifests, shared docs          | `n00-frontiers` governance rules              | Tag + `pnpm run validate:schemas` before export      |
| `n00-frontiers`    | Templates, CLI, quality guardrails       | `n00-cortex` schemas                          | `nox -s validate_templates_all` + docs diff          |
| `n00t`             | MCP surface, capability manifest         | `.dev/automation/scripts/*` outputs           | Update `n00t/capabilities/manifest.json` + emit logs |
| `n00tropic`        | Generators, briefs, operational doctrine | `n00-frontiers` rules, `n00-cortex` manifests | Regenerate via `n00tropic_cli` and archive outputs   |
| `n00plicate`       | Token and UI bundles                     | `n00-frontiers` design tokens                 | `pnpm exec antora` + bundle snapshot                 |
| `1. Cerebrum Docs` | ADRs, release notes                      | Automation artifacts                          | `workspace-release.sh` runs cleanly                  |

Any repo that needs an asset from a sibling must reference the published artifact (schema tag, template export, Antora site) rather than reading files across directories.

## Formatter guardrails

- **Python format flow**: Every Trunk config runs `isort@7.0.0` before `black@25.x` so imports settle before layout styling. If a formatter loop appears, run `trunk fmt --filter=isort,black` or `isort . && black .` in the affected repo.
- **isort configuration**: `n00-frontiers/.isort.cfg` pins `profile = black` and `line_length = 120`, and the setting is mirrored by the other repos via Trunk sync so Black never rewrites imports immediately after isort.
- **Deep dive**: See `n00-school/in-dev-learnings/black-isort-conflicts.md` plus `n00-frontiers/docs/quality/formatting-style.md` for the rationale, escalation steps, and verification checklist agents should follow when formatters disagree.
- **Automation reminder**: `trunk-upgrade.sh` (and the `python3 cli.py trunk-upgrade` helper) keep formatter versions in lockstep across every repo, so rerun it whenever `isort`/`black` ship compatibility fixes.
- **Python linting helper**: run `pnpm run lint:python` in the workspace root to run `isort`, `black` and `ruff` checks across Python subprojects. The workspace CI now runs `pnpm run lint:python` as part of `workspace-health` to validate Python formatting and lint checks in PRs.

## Trunk control vs. subrepo autonomy

To validate all subrepos centrally while preserving subrepo autonomy, the workspace CI runs the root helper script (`pnpm run trunk:check-all`) that executes `trunk check` in each subrepo. Each subrepo's `.trunk/trunk.yaml` still governs behavior for developer workflows and PR-bottom checks. This avoids conflicts and ensures CI-level uniformity.

- Root CI behavior: `pnpm run trunk:check-all` iterates over repo folders and runs `trunk check` in each, capturing JSON artifacts in `artifacts/trunk-results/`.
- Subrepo behavior: Each subrepo provides its own `.trunk/trunk.yaml`. If a subrepo lacks a `.trunk` directory, the workspace runner still runs `trunk check` with default settings and fail/record findings.

Tip: If you see 'unsupported linter' errors locally for `trunk` checks, run `pnpm run trunk:sync-defs` to copy the workspace standard definitions into each subrepo's `.trunk/trunk.yaml` (only when the subrepo needs the definitions locally). This avoids having to hand-edit each repo and remains reversible.

## Dependency placement and storage guidance

- Keep shared developer tooling at the workspace root (`pnpm install` at the root) to avoid installing the same tool multiple times in each subrepo. For example, `@biomejs/biome` is a workspace-level dev-dependency. Use `pnpm -w exec biome` to run the workspace-installed Biome from a subrepo.
- Single-subrepo utilities (for example, Antora for documentation) belong inside the repo that needs them, or they can run centrally from the workspace Antora binary so CI/workflows invoke `pnpm -w exec antora`. The root package.json already lists `@antora/cli` and `@antora/site-generator`, which keeps that binary consistent.
- Avoid running `pnpm install` inside each `trunk` lint definition; instead run `pnpm install` once at the job start or on the developer machine at root. Trunk definitions should invoke `pnpm -w exec` (workspace) or `pnpm -C <repo> exec` to run a binary from a specific subrepo to conserve local storage.

Local commands:

```bash
# Run trunk checks across each subrepo (same script CI uses):
pnpm run trunk:check-all

# Run the workspace-level Python checks (isort, black, ruff) locally:
pnpm run lint:python
```

## Operating guidelines

- **Plan in public**: Capture cross-repo decisions in `1. Cerebrum Docs/ADR/` and link to repo-specific ADRs.
- **Keep repos pristine**: Use `.dev/` directories for scratch assets and avoid committing generated artifacts.
- **Run the workspace maintenance loop**: Follow `1. Cerebrum Docs/WORKSPACE_MAINTENANCE.md` (plus the `AI_WORKSPACE_PLAYBOOK.md` companion) to run `workspace-health`, `meta-check`, and project preflights before every PR or release.
- **Version discipline**: Update `n00-cortex/data/toolchain-manifest.json` first when bumping runtimes so Renovate presets and generators stay aligned.
- **Release sequencing**: Tag repos independently, then run `workspace-release.sh` to snapshot versions and update documentation.
- **Security hygiene**: Run `pip-audit -r n00-frontiers/requirements.txt` (or rely on `meta-check`) before shipping templates.
- **Automation discovery**: Use `n00t/capabilities/manifest.json` to discover scripted operations for CLI or MCP clients.

## Workspace filesystem

Operational outputs live in the shared filesystem at `/Volumes/APFS Space/n00tropic`, organized as:

- `01-Leadership/`: governance, legal, and risk artifacts with links back to `n00tropic/01-Leadership`.
- `02-Revenue/`: campaign results, CRM exports, and sales intelligence synced from ERPNext.
- `03-Delivery/`: project deliverables, QA evidence, and support transcripts tied to ERPNext projects.
- `04-People/`: HRMS snapshots, onboarding packs, and n00-school evaluation summaries.
- `05-Finance-Procurement/`: accounting closes, purchasing approvals, and vendor records.
- `06-Innovation-Labs/`: R&D experiment outputs spanning `n00-frontiers`, `n00-cortex`, and `n00plicate`.
- `07-Platform-Ops/`: automation runbooks, telemetry, and ERPNext self-hosting playbooks.
- `99-Clients/`: per-client deliverables using the `@slug` naming convention.
- `90-Archive/`: immutable exports with checksums for audits.
- `98-Scratchpad/`: temporary drafts purged automatically after 30 days.

## Getting started locally

1. Clone the workspace: `git clone git@github.com:n00tropic/n00tropic-cerebrum.git && cd n00tropic-cerebrum`.
1. Initialize submodules: `git submodule update --init --recursive`.
1. Run `.dev/automation/scripts/workspace-health.sh --sync-submodules --publish-artifact --json` (optionally `--clean-untracked`) to align submodules and snapshot git state for agents and CI.
1. Install toolchains per repo (Python venv for `n00-frontiers`, Node for `n00-cortex` and `n00t`, pnpm for `n00plicate`).
1. Open the multi-root VS Code workspace (`n00-cortex/generators/n00tropic-cerebrum.code-workspace`).
1. Run baseline checks: `./.dev/automation/scripts/meta-check.sh` followed by repo-specific health commands.
1. Explore `1. Cerebrum Docs/` for ADRs, Renovate setup, and onboarding guides.

### Docs development (Antora with pnpm)

Use `pnpm` for local development of the Antora documentation and workspace scripts:

1. Prepare `pnpm` via corepack (installs the correct pnpm distribution for your environment):

   ```bash
   corepack enable
   corepack prepare pnpm@latest --activate
   ```

2. Install workspace packages from the root folder:

   ```bash
   pnpm install
   ```

3. Build and preview the documentation using the bundled Antora packages:

   ```bash
   pnpm -C n00plicate exec antora antora-playbook.yml
   open n00plicate/build/site/index.html
   ```

Antora writes its site under `n00plicate/build/site/`. When publishing, use the documented release flow instead of copying build artifacts between repos.

## Script index

The `script_index.md` file provides an automatically generated catalog of scripts (shell, Python, Node, etc.) across the polyrepo, and xref:script-index.adoc[] surfaces a curated Antora summary for agents.

- Browse the docs-native view via xref:script-index.adoc[] when you need the high-level breakdown.
- View the Markdown export directly (`script_index.md`) to scan every script path and description.
- Regenerate both outputs by running `python generate_script_index.py --workspace-root "/Volumes/APFS Space/n00tropic"` whenever new scripts land or categories shift.
- Follow the listed relative paths to jump into the owning repo before executing a script so dependency assumptions stay correct.

## Contribution reminders

Keep each repo automation-aware yet decoupled: evolve generators, docs, and agents in their own submodules while sharing release cadence via this workspace. Only update generated artifacts through their source commands, and capture cross-repo intent in `1. Cerebrum Docs/ADR/` before tagging releases.

> ❗️ Don't run `git init` in `/Volumes/APFS Space/n00tropic`. The organizational root stays non-versioned; start work from this repo or a submodule instead.
