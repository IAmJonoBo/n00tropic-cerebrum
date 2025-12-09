# AGENTS.md

A concise, agent-facing guide for n00HQ. Keep it short, concrete, and enforceable.

## Project Overview

- **Purpose**: SwiftUI host app for the n00tropic superproject—workspace control,
  dashboards, and UI shell.
- **Critical modules**: (scaffolding only)
- **Non-goals**: Not yet production-ready; hooks to workspace graph and automation
  are pending.

## Status

⚠️ **Scaffolding only.** Core functionality not yet implemented.

Planned features:

- Workspace graph / capability health visualization
- Automation control integration
- Dashboard shell

## Build & Run

### Prerequisites

- macOS 14+ (Swift 6 toolchain)
- Xcode 16+

### Common Commands

```bash
cd n00HQ
swift build
swift run n00hq
```

## Code Style

- **Swift**: Swift 6; SwiftUI views.
- **Architecture**: TBD—follow n00-dashboard patterns when implementing.

## Security & Boundaries

- Do not commit credentials or secrets.
- Follow workspace conventions once implementation begins.

## Definition of Done

- [ ] Build succeeds (`swift build`).
- [ ] Tests pass (when added).
- [ ] PR body includes rationale and test evidence.

## Integration with Workspace

When in the superrepo context:

- Root `AGENTS.md` provides ecosystem-wide conventions.
- Will integrate with workspace graph once implemented.
- Follow `n00-dashboard` patterns for Control Tower integration.

---

_For ecosystem context, see the root `AGENTS.md` in n00tropic-cerebrum._

_Status: Scaffolding only — under construction._

---

_Last updated: 2025-12-01_
