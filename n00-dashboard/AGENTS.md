# AGENTS.md

A concise, agent-facing guide for n00-dashboard. Keep it short, concrete, and enforceable.

## Project Overview

- **Purpose**: macOS/iPadOS SwiftUI companion for the Control Tower—read-only dashboard that watches lifecycle-radar and control-panel artefacts, surfacing readiness signals operators see in Markdown.
- **Critical modules**: `Sources/ControlTower/`, `Tests/`
- **Non-goals**: Do not implement write operations until Milestone 2; read-only for now.

## Ecosystem Role

```text
.dev/automation/artifacts/ → n00-dashboard (SwiftUI) → Visual readiness signals
          ↓
n00t capabilities (future bridge)
```

- **Consumes**: Lifecycle radar JSON, control panel Markdown.
- **Produces**: Visual dashboard for operators.
- **Future**: MCP/n00t surface bridge (Milestone 2+).

## Build & Run

### Prerequisites

- Xcode 16+ with Swift 5.10 toolchain
- macOS 15+ for desktop target
- Workspace artefacts must exist (run scripts first)

### Common Commands

```bash
# Generate required artefacts first
../.dev/automation/scripts/project-lifecycle-radar.sh
../.dev/automation/scripts/project-control-panel.py

# Build via CLI
cd n00-dashboard
swift build

# Build with tests
swift build --build-tests

# Run tests
swift test

# Or use VS Code task
# "swift: Build All (n00tropic-cerebrum/n00-dashboard)"
```

## Code Style

- **Swift**: Swift 5.10; SwiftUI views; SwiftFormat enforced.
- **Architecture**: Stores, Views, Capability separation.
- **Tests**: Fixture-driven XCTest.

## Security & Boundaries

- Read-only operations only (Milestone 1).
- Do not shell out to scripts in production (use Capability layer).
- Do not commit credentials or secrets.
- Logs emit to `n00-dashboard/artifacts/` for parity with CLI telemetry.

## Definition of Done

- [ ] Build succeeds (`swift build`).
- [ ] Tests pass (`swift test`).
- [ ] SwiftFormat passes.
- [ ] Views render with fixture data.
- [ ] PR body includes rationale and test evidence.

## Project Structure

```
Sources/
  ControlTower/
    Stores/          # File watchers + JSON decoders
    Views/           # SwiftUI components (RadarView, JobListView)
    Capability/
      ScriptRunner.swift  # Shell wrapper for radar/panel scripts
Tests/
  ControlTowerTests/     # Fixture-driven tests
```

## Dashboard Views

| View            | Data Source                          |
| --------------- | ------------------------------------ |
| Lifecycle Donut | `lifecycle-radar.json`               |
| Warnings Panel  | Metadata/consolidation warnings      |
| Job Table       | `control-panel.md` from n00-horizons |

## Key Files

| Path                        | Purpose           |
| --------------------------- | ----------------- |
| `Package.swift`             | SwiftPM manifest  |
| `Sources/ControlTower/`     | Main app source   |
| `Tests/ControlTowerTests/`  | Unit tests        |
| `docs/control-tower-app.md` | Architecture plan |

## Milestones

1. **Milestone 1** (current): Read-only dashboard
2. **Milestone 2**: Automation runners (preflight, radar regen)
3. **Milestone 3**: MCP/n00t surface bridge

## Integration with Workspace

When in the superrepo context:

- Root `AGENTS.md` provides ecosystem-wide conventions.
- Requires artefacts from `.dev/automation/artifacts/project-sync/`.
- Uses VS Code tasks for build integration.

---

_For ecosystem context, see the root `AGENTS.md` in n00tropic-cerebrum._

---

_Last updated: 2025-12-01_
