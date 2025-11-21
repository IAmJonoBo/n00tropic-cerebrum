# Renovate workspace presets

This directory contains shared Renovate presets for the workspace.

## Usage

- For the repository that contains these presets (the workspace root), reference the local preset in `renovate.json`:

```json
{
  "extends": ["local>renovate-presets/workspace.json"]
}
```

- For downstream repositories (that live in other repos), extend the preset using the `github>` reference:

```json
{
  "extends": [
    "github>n00tropic/n00tropic-cerebrum//renovate-presets/workspace.json"
  ]
}
```

## Migration helper

Use `.dev/automation/scripts/update-renovate-extends.py` to add or synchronize the required `extends` to all local `renovate.json` files. Run with `--apply` to modify files.

## Notes

- To avoid accidental divergence, the workspace's `renovate/presets/workspace.json` and `renovate-presets/workspace.json` are both maintained here for backwards compatibility; prefer `renovate-presets` for new references.
- Keep per-repo overrides minimal and only for things that cannot be represented in the shared preset.
