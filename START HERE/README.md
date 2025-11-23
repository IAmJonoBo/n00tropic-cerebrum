# Start Here: n00tropic Cerebrum Workspace

> The federated polyrepo that powers n00tropic’s automation engine, templates, and cross-repo governance.

## If you only have 5 minutes

- Scan the [workspace README](../README.md) for the ecosystem map and automation flow.
- Pick the repository that matches your task using the table below.
- Run `.dev/automation/scripts/meta-check.sh` from this workspace before opening a PR; it exercises shared policies.

## Repository map

| Repo                | Role                                                                | Start here                              |
| ------------------- | ------------------------------------------------------------------- | --------------------------------------- |
| `1. Cerebrum Docs/` | Workspace governance, ADRs, shared tooling policy                   | `1. Cerebrum Docs/START HERE/README.md` |
| `n00-frontiers/`    | Defines frontier-grade delivery standards and templates             | `n00-frontiers/START HERE/README.md`    |
| `n00-cortex/`       | System-of-record schemas + rule enforcement derived from frontiers  | `n00-cortex/START HERE/README.md`       |
| `n00tropic/`        | Flagship generator/service; orchestrates briefs → scaffolded assets | `n00tropic/START HERE/README.md`        |
| `n00t/`             | MCP control centre + automation host                                | `n00t/START HERE/README.md`             |
| `n00plicate/`       | Platform-agnostic design system + token orchestrator                | `n00plicate/START HERE/README.md`       |
| `n00-school/`       | Training lab for agents & evaluation pipelines                      | `n00-school/START HERE/README.md`       |

## Workspace automation checklist

1. **Bootstrap tooling** – `./.dev/scripts/bootstrap-trunk-python.sh` (only if Trunk cannot download runtimes automatically).
2. **Refresh sources** – `./.dev/automation/scripts/refresh-workspace.sh`.
3. **Meta-check** – `./.dev/automation/scripts/meta-check.sh` (runs lint/test suites per repo).
4. **Release snapshot** – `./.dev/automation/scripts/workspace-release.sh` (writes `1. Cerebrum Docs/releases.yaml`).
5. **Installs** – root `pnpm install` is blocked; use subrepo installs or `pnpm --filter`. JS subrepos have preinstall guards; rerun installs via `scripts/normalize-workspace-pnpm.sh` to enforce toolchain pins.
6. **Python deps** – locked with `uv`; verify via `pnpm run python:lock:check`.
7. **Alerts** – set `DISCORD_WEBHOOK` (and optional `REQUIRED_RUNNER_LABELS`) for runner and Python lock notifications.
8. **Secrets** – copy `.env.example` to `.env` in the workspace root; run `scripts/sync-env-templates.sh` to fan out `.env.example` stubs to subrepos. Keys: `GH_TOKEN`, `GITHUB_TOKEN`, `DISCORD_WEBHOOK`, `REQUIRED_RUNNER_LABELS`.
9. **CLI shortcuts** – prefer `python3 cli.py health-toolchain|health-runners|health-python-lock|normalize-js` for common checks; they wrap the canonical scripts with logging.

These scripts back the `workspace.*` capabilities exposed through `n00t/capabilities/manifest.json`.

## Guardrails

- **Keep code in the right repo**: automation scripts and schemas belong under `n00tropic-cerebrum/`; operational handbooks, client assets, or brand deliverables stay in the organisation root (`/Volumes/APFS Space/n00tropic`).
- **No generated artefacts in git**: MkDocs `site/`, Storybook builds, token outputs, and ERPNext exports should remain ignored and published via pipelines or generated on demand.
- **Link back to policy**: any cross-repo decision must land in `1. Cerebrum Docs/ADR/` with references to the repo-specific ADR.
- **Isolate client data**: never commit exports under `n00tropic-cerebrum/`; use the `99-Clients/` directory in the root workspace for sensitive deliverables.

## Next steps

- Need to reason about organisational policy? Jump to [`../START HERE/README.md`](../START%20HERE/README.md).
- Wiring a new automation? Add the script under `../.dev/automation/scripts/`, expose it from `n00t/capabilities/manifest.json`, and document usage in the relevant repo’s `START HERE`.
- Looking for Renovate or Trunk conventions? See `1. Cerebrum Docs/RENOVATE_SETUP.md` and `1. Cerebrum Docs/TRUNK_GUIDE.md`.
- Attaching an agent or ephemeral workspace? Review `1. Cerebrum Docs/AI_WORKSPACE_PLAYBOOK.md` for topology, payload formats, and cleanup recipes.
