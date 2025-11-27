# Workspace Maintenance Runbook

This guide keeps the federated workspace healthy whether you are preparing a pull request or refreshing a long-lived clone.

## 1. Assess the Workspace

```bash
./.dev/automation/scripts/workspace-health.sh --strict-submodules --publish-artifact --json
```

- **Goal**: ensure every submodule is clean and aligned with its upstream.
- `--publish-artifact` writes the JSON snapshot to `artifacts/workspace-health.json` so agents and CI can ingest it without rerunning the script.
- Add `--sync-submodules` when reviving a stale clone, or `--fix-all` to run submodule + trunk sync together.
- Use `--clean-untracked` to safely drop generated files; it only runs `git clean -fd` inside repos that have _no_ tracked changes.
- Use `--repo-cmd n00-cortex:"git status -sb"` for quick targeted diagnostics.
- See `AI_WORKSPACE_PLAYBOOK.md` for the agent-oriented cheatsheet (workspace topology, payload formats, and remediation flow).

## 2. Fix Drift (if needed)

| Scenario                                            | Action                                                                                        |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Submodule has untracked changes you want to discard | `git -C <repo> checkout -- .` or run `workspace-health --repo-cmd <repo>:"git checkout -- ."` |
| Submodule is behind                                 | `git -C <repo> pull --ff-only`                                                                |
| Tooling configs diverged                            | `./.dev/automation/scripts/sync-trunk.py --pull` (automatically included in `--fix-all`)      |
| Only untracked files remain (root or submodule)     | `./.dev/automation/scripts/workspace-health.sh --clean-untracked`                             |
| Workspace root dirty                                | Commit or stash before release automation                                                     |

## 3. Run Cross-Repo Checks

```bash
./.dev/automation/scripts/meta-check.sh
```

This script runs schema validation, Renovate preset verification, CVE scans, and other repo-specific linters.

For a fast human-friendly snapshot of the workspace state while you are iterating locally, call the MCP capability `workspace.status` (preferred for agents) or run the helper script directly:

```bash
./.dev/automation/scripts/workspace-status.sh
```

Both entrypoints print a short root `git status`, submodule summary, and (when installed) a Trunk summary for the root repo.

When submodules have moved forward (for example, after you have committed and pushed changes inside `n00-cortex` or `n00-frontiers`), you can capture the new "machine state" in the superrepo with:

```bash
./.dev/automation/scripts/workspace-commit-submodules.sh
```

This stages all submodule paths in the root repo and creates a single commit that pins the updated SHAs, so you can follow with a simple `git push`.

Agents (or humans) who just need to verify submodule hygiene without the full `workspace.gitDoctor` payload can invoke `workspace.checkSubmodules`, which shells out to `check-submodules.sh` and fails fast on dirty submodules, detached HEADs, or upstream drift.

When manifests or repos drift from the skeleton definition, `workspace.checkSkeleton` mirrors `check-workspace-skeleton.py` so you can audit required directories, scaffold missing stubs with `apply=true`, and optionally bootstrap pnpm/trunk when reviving older clones.

## 4. Validate Delivery Artefacts

For any metadata-bearing document (ideas, jobs, projects):

```bash
./.dev/automation/scripts/project-preflight.sh --path <doc> --registry <optional registry override>
```

Preflight chains capture, GitHub sync, and ERPNext sync to confirm IDs, links, and review cadence before you share updates.

## 5. Document & Ship

1. Capture relevant ADRs in `1. Cerebrum Docs/ADR/`.
2. Commit per-repo changes and push.
3. Run `./.dev/automation/scripts/workspace-release.sh` when tagging a coordinated drop so release manifests stay in sync.

> Tip: wire the workflow above into automation pipelines (Trunk, CI) to fail fast whenever the workspace drifts.

## AI / Agent Quick Reference

- Preferred capability: `workspace.gitDoctor` (backed by `workspace-health.sh`). Payload keys include `cleanUntracked`, `syncSubmodules`, `publishArtifact`, and `strict`.
- Fast preflight: `workspace.doctor` runs Renovate token checks, Trunk config sync, and pnpm dependency checks; pass `mode=fix` to apply repairs.
- Lightweight hygiene check: `workspace.checkSubmodules` mirrors `.dev/automation/scripts/check-submodules.sh` so you can gate releases on submodule cleanliness without running the full doctor sweep.
- Skeleton enforcement: `workspace.checkSkeleton` wraps `check-workspace-skeleton.py` for manifest/skeleton validation plus optional `apply` or `bootstrap` flows.
- JS toolchain reset: `workspace.normalizePnpm` reuses `normalize-workspace-pnpm.sh` to delete `node_modules/.pnpm` trees and reinstall with the pinned pnpm version across templates/examples.
- Node version propagation: `workspace.syncNvmrc` links subrepo `.nvmrc` files back to the workspace pin (set `force=true` to override repo-specific pins).
- Python env hygiene: `workspace.venvHealth` fronts `venv-health.sh` so agents can inventory/prune `.venv-*` directories or refresh them from requirements files.
- Trunk upgrades: `workspace.trunkUpgradeWorkspace` encapsulates `scripts/trunk-upgrade-workspace.sh` to refresh linters, sync configs, and (optionally) run trunk check/fmt across subrepos.
- Trunk orchestration: `trunk.manage` (sync/pull/push/upgrade/fmt) and `trunk.sync` (check/pull/push with JSON reporting) keep downstream configs aligned; `trunk.runSubrepos` runs trunk fmt/check across subrepos; `trunk.lintSetup` installs/initialises the CLI when missing.
- Automation emits `artifacts/workspace-health.json`, which distinguishes tracked vs untracked entries per repo so agents can react programmatically.
- Branch hygiene: `merge.minimalSet` merges eligible automerge PRs; `branches.wrangle` files a cleanup issue (and can auto-delete with `autoDelete=true`); `branches.auditTemp` emits a markdown branch report under `artifacts/tmp/branch-wrangler/`.
- Check polling: `checks.waitForChecks` / `checks.waitForPrChecks` monitor GitHub check-runs until success/failure/timeout for handoffs that need a definite gate.
- Telemetry helpers: `telemetry.recordRunEnvelope` and `telemetry.recordCapabilityRun` append JSONL run records under `.dev/automation/artifacts/automation/` for dashboards.
- Additional context and sample payload LIVE in [`AI_WORKSPACE_PLAYBOOK.md`](AI_WORKSPACE_PLAYBOOK.md).

## Branch merging helpers

- A workspace workflow `Merge to minimal set` is available to help merge PRs that are labeled `automerge`. This workflow runs on manual dispatch and merges PRs that are mergeable and labeled `automerge` to `main`.
- Use the label `automerge` for PRs that have already been reviewed and have passing checks; the automation only merges PRs that are mergeable and won't force-merge PRs with conflicts or failing checks.
- To trigger the merge automation manually, run the workflow `Merge to minimal set` from the Actions tab or use the capability `merge.minimalSet` from the MCP CLI to run it programmatically.
