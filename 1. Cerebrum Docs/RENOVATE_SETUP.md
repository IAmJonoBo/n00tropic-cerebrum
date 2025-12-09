# Renovate Setup

All repositories now inherit dependency policy from the shared preset published in `n00tropic-cerebrum/renovate-presets/workspace.json`. To keep hosted Renovate aligned:

1. **Self-hosted or GitHub App**
   - Ensure the bot has read access to `n00tropic-cerebrum`.
   - Update the global configuration (or onboarding preset) to extend `github>n00tropic/n00tropic-cerebrum//renovate-presets/workspace.json`.
   - Remove legacy `config:base` or workspace-specific overrides unless they are still required.
2. **Enterprise mirrors**
   - If outbound GitHub downloads are blocked, mirror `n00tropic-cerebrum/renovate-presets/workspace.json` to an internal repository.
   - Replace the `github>` reference with your internal mirror (for example, `local>renovate-presets/workspace.json`).
3. **Verification**
   - After updating the preset, trigger Renovate manually on `n00-frontiers` and `n00plicate` (or any downstream repository that extends the preset).
   - Confirm the dashboard PR reflects the new preset and grouped rules.

Downstream repositories should not redefine high-level scheduling or semantic commit behaviour; keep adjustments minimal (for example, package-specific automerge rules). A lightweight `renovate.json` that only extends the workspace preset and declares local packageRules is the recommended pattern:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "github>n00tropic/n00tropic-cerebrum//renovate-presets/workspace.json"
  ],
  "packageRules": [
    {
      "matchManagers": ["npm"],
      "automerge": true,
      "matchUpdateTypes": ["minor", "patch"]
    }
  ]
}
```

## Integrating Additional Tooling

- **pip-tools (`pip-compile`)** – Generate deterministic `requirements.txt` files; configure Renovate `postUpgradeTasks` to run `pip-compile` for Python projects.
- **pip-audit / Safety** – Add to CI pipelines (for example via `.dev/automation/scripts/meta-check.sh`) to block merges when known CVEs exist.
- **Node lockfiles** – Ensure `package-lock.json`/`pnpm-lock.yaml` are committed so Renovate upgrades stay reproducible.
- **Custom dashboards** – Use Renovate's dependency dashboard or consume data from the Renovate API to track stale upgrades across repos.
