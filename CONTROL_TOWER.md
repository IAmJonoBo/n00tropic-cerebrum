# ControlTower (Swift)

Workspace-local control CLI for the n00tropic superproject.

Build/Run:
```bash
cd /Volumes/APFS Space/n00tropic/n00tropic-cerebrum
swift run control-tower help
```

Commands:
- `status` – show detected workspace paths (package root, n00-cortex location).
- `validate-cortex` – run `pnpm run validate:schemas` inside `n00-cortex`.
- `graph-live` – rebuild catalog graph with live workspace inputs.
- `graph-stub` – rebuild graph using only in-repo assets (CI-safe).
- `sync-n00menon` – run `pnpm run docs:sync-n00menon --write` to pull doc updates into the workspace.

Notes:
- The binary assumes `n00-cortex` lives at `<workspace-root>/n00-cortex`.
- Commands stream stdout/stderr directly; non-zero exits are surfaced.
- pnpm 10.23.0 is invoked via `npx pnpm@10.23.0` for cortex validation.
