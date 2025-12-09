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

- **Concurrency caps:** Every capability inherits `guardrails.max_concurrency` (default `1`). Bump the value when the backing script is idempotent and can safely overlap, otherwise keep it at `1` to serialize disk-heavy routines like `workspace.gitDoctor`.
- **Output redaction:** Populate `guardrails.redact_patterns` with regexes for API keys, tokens, or client names; anything matched is swapped with `guardrails.redact_replacement` (default `[redacted]`) before stdout/stderr reach agents.
- **Log size limits:** The server truncates stdout/stderr via `guardrails.stdout_max_bytes` / `stderr_max_bytes`. Increase these when a capability must stream structured JSON, decrease them when only final summaries matter.
- **Telemetry tagging:** Optional `guardrails.telemetry_tags` (e.g., `{ "category": "workspace", "pii": "none" }`) travel with every start/finish event so dashboards can pivot by capability family.
- **Runtime hooks:** Set `N00T_MCP_TELEMETRY_PATH` to capture JSONL start/finish envelopes for each capability. The file is append-only, ordered, and respects the redaction rules above, making it safe to sync into `.dev/automation/artifacts/automation/` for historical analysis.

## New pipelines (Dec 2025)

- **Workflow compiler:** `n00tropic_cli design workflow compile --dsl path/to/workflow.yaml --target artifacts/workflows/... [--simulate]` validates DSL against Cortex schema and emits agent configs + run script. Telemetry hints are dropped alongside outputs for meta-learner consumption.
- **Guardrail/routing spans:** `observability.py` and `observability-node.mjs` now emit `guardrail.decision` (with `guardrail.prompt_variant`) and `router.selection` spans. Dashboards aggregate via `artifacts/telemetry/edge-dashboard.json`.
- **Workspace CLI:** `./bin/workspace` wraps the canonical automation flows (`health`, `meta-check`, `release-dry-run`, `deps-audit`, `ingest-frontiers`, `render-templates`) for quicker operator and agent use; scripts still live under `.dev/automation/scripts/`.
- **Parallel flags:** `meta-check.sh` and `scripts/sync-venvs.py` accept `--jobs N` (or env `META_CHECK_JOBS`) to parallelize eligible steps (venv sync, template render). Defaults stay serial for reproducibility.

## AGENTS.md Reference

Every subproject contains an `AGENTS.md` optimised for AI agent operation. These files provide:

- **Self-contained context**: Build/test commands, security boundaries, local conventions
- **Ecosystem awareness**: References to root AGENTS.md for cross-repo context
- **Standalone operation**: Works when repo is checked out in isolation (prevents detachment confusion)

| Resource          | Path                                                     |
| ----------------- | -------------------------------------------------------- |
| Root AGENTS.md    | `/AGENTS.md`                                             |
| Validation script | `.dev/automation/scripts/docs-agents-refresh.sh --check` |
| MCP capability    | `docs.refresh` with `mode=check`                         |

When entering a new context, agents should read the closest `AGENTS.md` first.
