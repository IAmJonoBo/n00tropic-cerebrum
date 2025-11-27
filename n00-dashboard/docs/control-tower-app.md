# Control Tower Companion App – Concept & Architecture

## Goals

1. Give humans and agents a single SwiftUI workspace for viewing lifecycle readiness (radar), preflight blockers, and outstanding jobs without leaving the native dashboard.
2. Orchestrate n00t capabilities (preflight, lifecycle radar, control panel, record job/idea) from a guided UI so operators run the right automation with the right context.
3. Keep today’s file-centric workflows intact: the app reads/writes Markdown + JSON artefacts generated under `.dev/automation/artifacts/**` and links back to the existing runbooks.
4. Provide a north-star UX that can grow into a full orchestration hub, but ship incrementally so current docs/scripts remain the system of record.

## High-Level Architecture

```text
+------------------------------------------------------------+
| SwiftUI App (macOS + iPadOS target)                        |
|                                                            |
|  - ControlTowerView (radar + blockers)                     |
|  - JobBoardView (metadata table + filters)                 |
|  - CapabilityRunnerView (n00t automation surface)          |
|  - TimelineView (recent artefacts, agent runs)             |
+------------------------------------------------------------+
              |                  |                    |
   JSON ingest layer      Capability bridge    File-system writer
 (radar/preflight/jobs)     (n00t CLI/MCP)    (control-panel.md)
```

### Modules

| Module                 | Responsibilities                                                                                                                                   | Notes                                                      |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `RadarStore`           | Load `lifecycle-radar.json`, derive chart data, expose Combine publishers for SwiftUI charts.                                                      | Watches file changes via `DispatchSourceFileSystemObject`. |
| `PreflightStore`       | Index `*-preflight.json` artefacts, compute freshness, surface blockers grouped by job.                                                            | Shared with notification center integration.               |
| `JobCatalogStore`      | Read metadata from `n00-horizons/jobs/**/README.md` (via the same YAML parser logic wrapped in a Swift bridge).                                    | Provide quick filters (owner, lifecycle, review window).   |
| `CapabilityBridge`     | Invoke `.dev/automation/scripts/*.sh` through `Process`, capture stdout/stderr, and persist transcripts to `artifacts/automation/agent-runs.json`. | Aligns with existing n00t telemetry.                       |
| `ControlPanelExporter` | Call `project-control-panel.py` and surface the resulting Markdown + share/export options.                                                         | Keeps Markdown as the source of truth.                     |
| `n00tClient`           | Future: wrap MCP over WebSockets so the app can list & trigger capabilities without shelling out.                                                  | Planned after CLI parity.                                  |

### Data Flow

1. **Startup**: stores read cached JSON/Markdown and render immediately. File-system observers refresh sections when artefacts are rewritten by automation or the CLI.
2. **User runs Preflight**: CapabilityRunner asks for doc path, shells out to `project-preflight.sh`, pipes stdout/stderr into a log view, then refreshes PreflightStore + ControlPanelExporter.
3. **Control Panel**: At any time the operator taps “Regenerate Control Panel,” which chains `project-lifecycle-radar.sh` → `project-control-panel.py` and opens the Markdown preview inside the app alongside a share/export button.
4. **Notifications**: When RadarStore detects new “overdue” entries or PreflightStore sees `status = attention`, the app surfaces badges (and can push notifications) without waiting for daily email updates.

## UI & Navigation

- **Home / Control Tower**: split view with (a) lifecycle donut or bar chart, (b) list of top issues (overdue reviews, missing integrations, failing preflights), (c) quick links (runbook, task-slice playbook, control panel Markdown).
- **Jobs**: table with filters, inline indicators for review date proximity, tap to open the Markdown in VS Code/Xcode, or run Preflight from action menu.
- **Automation**: list of curated capabilities (preflight, lifecycle radar, control panel, record-job, record-idea) with human-friendly forms mirroring CLI flags. Each run logs to telemetry and exposes copyable JSON.
- **n00t Surface**: placeholder for future integration—links out to the existing MCP UI but defines the embedding points (web view or native client once the MCP SDK lands).

## UID / Visual Language

- Reuse n00tropic frontier palette (dark slate background, neon accent) but align with SwiftUI’s native components for accessibility.
- Icons: SF Symbols (e.g., `gauge.high` for radar, `exclamationmark.shield` for blockers, `doc.text.magnifyingglass` for jobs). Provide a custom glyph for “Control Tower” to reuse across docs and slides.
- Status chips: `ok` (green), `attention` (amber), `blocked` (red) to stay consistent with capability outputs.

## Rollout Plan

1. **Milestone 1 – Read-Only Dashboard**
   - Implement stores + file watchers.
   - Ship ControlTowerView + JobBoardView reading existing artefacts.
   - Add manual refresh buttons calling the scripts.
2. **Milestone 2 – Automation Runner**
   - Wrap key scripts/capabilities.
   - Persist run logs + link to artefacts.
3. **Milestone 3 – n00t Integration**
   - Embed MCP auth, allow browsing/triggering remote actions.
   - Add notifications for drift/preflight failures.
4. **Milestone 4 – UI Polish & Export**
   - Native rendering of control-panel Markdown (Swift MarkdownUI), share sheet, export to PDF for leadership reviews.

## Open Questions

- Authentication for GitHub/ERPNext when the app eventually calls APIs directly—initial releases will delegate to existing scripts so secrets stay in the CLI env.
- Packaging: ship as part of `n00-dashboard` target with notarised builds, or as an internal Swift Package consumed by both macOS/iPadOS variants?
- Multi-user telemetry: need a lightweight sync (maybe publish run summaries to a shared bucket) so Control Tower status is consistent across machines.

Each milestone should map to an entry under `n00-horizons/jobs/` so the Swift roadmap stays traceable alongside the existing automation assets.
