# Golden Path: n00-dashboard

> **Quick Ref**: `AGENTS.md` is the primary agent-facing reference; this file summarises the happy-path workflow.

## 1. Prerequisites

- Xcode 16+ with Swift 5.10 toolchain
- macOS 15+

## 2. Generate Artefacts

```bash
../.dev/automation/scripts/project-lifecycle-radar.sh
../.dev/automation/scripts/project-control-panel.py
```

## 3. Build & Test

```bash
cd n00-dashboard
swift build
swift build --build-tests
swift test
```

## 4. VS Code Integration

Use task: `swift: Build All (n00tropic-cerebrum/n00-dashboard)`

## 5. Key Documents

| Document    | Purpose           |
| ----------- | ----------------- |
| `AGENTS.md` | Agent-facing SSoT |
| `README.md` | Project overview  |

---

_Last updated: 2025-12-01_
