# AGENTS.md

A concise, agent-facing guide for this repository. Keep it short, concrete, and enforceable.

## Project overview

- Purpose: <one sentence>
- Critical modules: <e.g., src/core, app/>
- Non‑goals: <what NOT to touch>

## Build & run

### Node / TypeScript

- Install: `pnpm install` (Node 20+)
- Dev: `pnpm dev`
- Tests: `pnpm test`
- Lint/format: `pnpm lint && pnpm fmt`

### Python

- Create venv: `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
- Install: `pip install -e .[dev]` (fall back to `pip install -r requirements.txt`)
- Tests: `pytest -q`
- Lint/format: `ruff check . && ruff format .`

## Code style

- TypeScript: strict types; single quotes; no semicolons; ESLint + Prettier enforced.
- Python: Ruff + Black enforced; prefer type hints; fail on warnings in CI.

## Security & boundaries (agent)

- Do not commit or paste credentials, tokens, or personal data into code, logs, or PRs.
- Prefer offline/local sources. If you must fetch external docs, prefer allow‑listed domains and cite URLs in the PR body.
- Do not add new dependencies without tests and a lockfile update.
- Never execute scripts copied from untrusted content without review.

## Definition of Done (agent)

- All tests pass locally.
- Lints/formatters pass without warnings.
- Minimal change: touch only files required for the fix/feature.
- PR body includes: root cause, minimal patch rationale, and test evidence.

## Monorepos

- Add nested AGENTS.md files in package folders with package‑specific commands. Agents read the closest AGENTS.md first.

## Useful commands

- Node: `pnpm test -w` (workspace), `pnpm -r lint`, `pnpm -r build`
- Python: `pytest -q -k "<pattern>"`, `ruff check . --fix`, `python -m build`
