# Credentials Guide (workspace + subprojects)

Use short‑lived, least‑privilege tokens. Store them in your runner/agent environment (not in repo). Example shell exports below use placeholders you should replace.

## Workspace (superproject)

- `GH_SUBMODULE_TOKEN` (or `GITHUB_TOKEN`): `repo` scope for cloning private submodules and for Antora content fetch. Export before `scripts/bootstrap-workspace.sh` or `pnpm exec antora antora-playbook.yml`:
  ```bash
  export GH_SUBMODULE_TOKEN=ghp_yourtoken
  ```
- `TRUNK_BIN`: absolute path to the trunk CLI (v1.25.4) installed outside the repo. Example:
  ```bash
  export TRUNK_BIN="$HOME/.cache/trunk/bin/trunk"
  ```
- `OTEL_EXPORTER_OTLP_ENDPOINT` / `N00_DISABLE_TRACING`: set when running MCP servers or ai-workflow services to control telemetry.

## n00menon (docs SSoT)

- Reuses workspace `GH_SUBMODULE_TOKEN` for `docs:sync` (Antora/README sync).
- No extra secrets; GitHub Pages deploy uses repository permissions from CI.

## n00t (automation surface)

- `GH_SUBMODULE_TOKEN` for submodule fetch when running `scripts/bootstrap-workspace.sh` from the superproject.
- Optional: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` when exercising Azure AI routes in dev.

## n00-frontiers / n00-cortex / n00clear-fusion / n00tropic / n00-school / n00-horizons / n00plicate

- All use the shared `GH_SUBMODULE_TOKEN` for fetch; no additional credentials required for local builds.
- If Typesense search is enabled, set `TYPESENSE_API_KEY` + `TYPESENSE_HOST` in your shell before running search freshness scripts.

## Docker / Registry (optional)

- If pushing images (e.g., `n00menon`), log in first:
  ```bash
  export REGISTRY_USER=...
  export REGISTRY_TOKEN=...
  docker login ghcr.io -u "$REGISTRY_USER" -p "$REGISTRY_TOKEN"
  ```

## Notes

- Keep tokens out of logs; prefer env vars or a `.env.local` that is gitignored.
- For ephemeral agents, export the variables then run: `scripts/bootstrap-workspace.sh` → `pnpm install` → `scripts/bootstrap-python.sh` → docs/build steps.
