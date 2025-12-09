# Local hooks and proactive guards

- **Pre-push hook** (`.git/hooks/pre-push`): runs `scripts/tidy-submodules.sh` (sync/update submodules, manifest gate, skeleton check) plus the manifest gate directly. Keeps git links and the manifest aligned before pushes.
- **Manifest gate (CI + local)**: `.dev/automation/scripts/manifest-gate.sh` fails when git repos or `.gitmodules` entries are missing from `automation/workspace.manifest.json`.
- **Skeleton apply**: `python .dev/automation/scripts/check-workspace-skeleton.py --apply` scaffolds required dirs/stubs and backfills manifest entries.
- **Health auto remediate**: `python .dev/automation/scripts/workspace-health.py --auto-remediate --publish-artifact` applies skeleton, syncs submodules, safe-cleans untracked, and ensures default branches.
- **Subrepo wrappers**: `n00-cortex/.dev/n00-cortex/scripts/{workspace-health-wrapper.sh,skeleton-wrapper.sh}` and `n00t/.dev/n00t/scripts/{...}` forward to the root scripts when working inside those repos.

Usage tips:

- If a push is blocked, run `bash scripts/tidy-submodules.sh` directly to see the manifest/skeleton output.
- Add new repos via `scripts/bootstrap-repo.sh --name <repo> --role <role>` so manifest + skeleton stay consistent.
