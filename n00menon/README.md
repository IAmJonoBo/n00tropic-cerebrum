# n00menon — Centralized Docs Library

This is the canonical documentation library for the n00tropic workspace. It contains shared documentation patterns, templates, and curated content for workspace-wide reuse.

Use `pnpm` scripts to build and validate the docs:

```bash
pnpm -w install
pnpm -C n00menon run docs:ci
```

See CONTRIBUTING.md for contribution guidance and style rules.

To provision a self-hosted runner for strict docs builds, use the workspace helper:

```bash
bash .dev/automation/scripts/setup-docs-runner.sh
```
