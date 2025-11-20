# AI & Agent Workspace Playbook

AI assistants (and ephemeral agent sessions) frequently attach to this filesystem after the human operator has already been iterating. The notes below make it trivial to recover context, detect the active repo, and tidy up submodules or untracked files before attempting an automation run.

## Workspace Topology

- **Super root**: `/Volumes/APFS Space/n00tropic/` (intentionally _not_ a git repo). It houses the federated `n00tropic-cerebrum/` repo, the operational archive in `n00tropic_HQ/`, and shared automation under `.dev/`.
- **Primary git workspace**: `/Volumes/APFS Space/n00tropic/n00tropic-cerebrum/` with submodules for `n00t/`, `n00-frontiers/`, `n00-cortex/`, etc.
- **Automation scripts**: tracked inside `n00tropic-cerebrum/.dev/automation/scripts/`. Anything under the outer `.dev/` directory mirrors to local environments but is not versioned.

## Identify Your Repo Quickly

> ✅ When in doubt, run the script below – it enumerates the workspace root plus every submodule.

```bash
./.dev/automation/scripts/workspace-health.sh --publish-artifact
```

- Use `git rev-parse --show-toplevel` from any path to confirm which repo you are in.
- The script writes `artifacts/workspace-health.json`, which agents can parse to decide which submodule needs attention and whether the workspace root is ahead/behind origin.

## Sanity Checks & Auto-Remediation

| Need                                                      | Command                                                                   | Notes                                                                          |
| --------------------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Snapshot workspace + publish machine-readable status      | `./.dev/automation/scripts/workspace-health.sh --publish-artifact --json` | JSON goes to stdout **and** `artifacts/workspace-health.json`.                 |
| Clean only-untracked noise (e.g. generated assets) safely | `./.dev/automation/scripts/workspace-health.sh --clean-untracked`         | Runs `git clean -fd` for repos that have _no_ tracked changes.                 |
| Realign submodule pointers                                | `./.dev/automation/scripts/workspace-health.sh --sync-submodules`         | Equivalent to `git submodule sync && git submodule update --init --recursive`. |
| Run everything (submodules + trunk sync)                  | `./.dev/automation/scripts/workspace-health.sh --fix-all`                 | Alias for the previous two steps.                                              |
| Strict CI-style enforcement                               | Append `--strict-submodules --strict-root`                                | Causes a non-zero exit when anything is dirty/diverged.                        |

## n00t Capability: `workspace.gitDoctor`

- The capability manifest now exposes the script above at `workspace.gitDoctor`. It honours the following payload keys when invoked via `n00t`’s agent runner or MCP host:
  - `cleanUntracked` → toggles `--clean-untracked`.
  - `syncSubmodules` → toggles `--sync-submodules`.
  - `publishArtifact` → writes the JSON file to `artifacts/workspace-health.json`.
  - `strict`/`check` → mirrors the CLI `--strict` flag for CI checks.
- Results are persisted automatically when the runner sets `CAPABILITY_PAYLOAD.output`, so agents always have a JSON artefact to inspect after the run.

### Sample MCP payload

```json
{
  "cleanUntracked": true,
  "syncSubmodules": true,
  "publishArtifact": true,
  "strict": false
}
```

## Handling Dirty States Before Push

1. **Root shows tracked changes to a submodule** (`workspace-health` prints `tracked 1 ... n00t`):
   - Inspect the repo: `git -C n00t status -sb`.
   - Commit/push inside the submodule if the change is intentional, then commit the pointer change at the root.
   - Otherwise run `git submodule update --init --recursive` to reset to the recorded revision.
2. **Root shows untracked files only**:
   - Use `--clean-untracked` (safe, because it skips repos with tracked changes).
3. **Submodule behind/ahead**:
   - `git -C <repo> pull --ff-only` or `git -C <repo> push --force-with-lease` depending on the direction.

> Tip: the JSON artifact exposes `tracked` vs `untracked` arrays per repo, so an agent can branch its remediation strategy programmatically.

## Agent-Friendly Checklist

1. `workspace-health.sh --publish-artifact --json`.
2. Read `artifacts/workspace-health.json` to determine the active repo + remediation path.
3. Run guarded cleaners (`--clean-untracked`) or `--sync-submodules` as needed.
4. When invoked via MCP, prefer `workspace.gitDoctor` so the host automatically records the output path.

Following the loop above removes the guesswork around submodules, untracked files, and root vs submodule context before automation tries to run.
