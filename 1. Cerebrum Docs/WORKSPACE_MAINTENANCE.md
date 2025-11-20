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

For a fast human-friendly snapshot of the workspace state while you are iterating locally, you can also run:

```bash
./.dev/automation/scripts/workspace-status.sh
```

This prints a short root `git status`, submodule summary, and (when installed) a Trunk summary for the root repo.

When submodules have moved forward (for example, after you have committed and pushed changes inside `n00-cortex` or `n00-frontiers`), you can capture the new "machine state" in the superrepo with:

```bash
./.dev/automation/scripts/workspace-commit-submodules.sh
```

This stages all submodule paths in the root repo and creates a single commit that pins the updated SHAs, so you can follow with a simple `git push`.

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
- Automation emits `artifacts/workspace-health.json`, which distinguishes tracked vs untracked entries per repo so agents can react programmatically.
- Additional context and sample payload LIVE in [`AI_WORKSPACE_PLAYBOOK.md`](AI_WORKSPACE_PLAYBOOK.md).
