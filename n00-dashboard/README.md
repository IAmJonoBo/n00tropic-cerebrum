# n00-dashboard – Control Tower Companion

This target hosts the macOS/iPadOS SwiftUI companion for the Control Tower. Milestone 1 delivers a read-only dashboard that watches lifecycle-radar + control-panel artefacts and surfaces the same readiness signals operators see in Markdown.

> 🤖 **AI Agents**: Start with [`AGENTS.md`](./AGENTS.md) for agent-optimised build and test commands.

## Prerequisites

- Xcode 16 (or newer) with Swift 5.10 toolchain
- macOS 15+ for the desktop target
- Ensure the workspace artefacts exist: run from the repo root
  ```bash
  .dev/automation/scripts/project-lifecycle-radar.sh
  .dev/automation/scripts/project-control-panel.py
  ```

## Building the Read-Only Dashboard

1. Open the SwiftPM project (`n00-dashboard/Package.swift`) in Xcode **or** build via CLI:
   ```bash
   cd n00-dashboard
   swift build
   ```
2. Run the ControlTower target. The initial view loads:
   - Lifecycle donut (parsed from `.dev/automation/artifacts/project-sync/lifecycle-radar.json`)
   - Metadata/consolidation warnings list
   - Outstanding job table sourced from `n00-horizons/docs/control-panel.md`
   - “Refresh Signals” button that shells out to the two scripts above
3. Logs for each refresh live under `n00-dashboard/artifacts/` to keep parity with the CLI telemetry.

## Project Structure

```
Sources/
  ControlTower/
    Stores/          // File watchers + JSON decoders
    Views/           // SwiftUI components (RadarView, JobListView, WarningPanel)
    Capability/
      ScriptRunner.swift  // Shell wrapper for radar/panel scripts
Tests/
  ControlTowerTests/      // Fixture-driven tests (WIP)
```

## Next Steps

- Wire in automation runners (preflight, radar regen) for Milestone 2.
- Embed MCP/n00t surface once the bridge is available.
- Follow the detailed architecture plan in `docs/control-tower-app.md` for upcoming milestones.
