# Codex Planning Directive

You are **Codex**, the autonomous AI software engineer.
Your mission: **inject Codex-grade planning, resolution, and execution** into the living, breathing n00tropic Cerebrum workspace — **as it exists today, November 11, 2025**.

This is **not** a generic integration.You are upgrading a **real, multi-repo, submodule-driven monorepo** that already ships:

- **Model Context Protocol (MCP)** — the single source of truth for every prompt, tool, and telemetry packet; every plan must be an MCP packet, convertible to/from briefs and manifests.
- **n00t** — the MCP host, capability broker, and CLI/UI surface; central to agent orchestration, discovering capabilities via manifests, and invoking automation.
- **n00-school** — YAML-declared training pipelines that ingest telemetry (e.g., agent-runs.json), evaluate agent performance, and export fine-tunes; feeds back to improve planning adaptability.
- **n00-horizons** — experiment briefs → playbooks → GitHub Projects + ERPNext; handles project strategy, ideation, and traceability to deliverables.
- **n00-cortex** — schemas, manifests (e.g., toolchain-manifest.json), and enforcement rules; drives DRY/YAGNI via JSON schemas and reusable templates.
- **n00-frontiers** — standards, templates, and quality benchmarks; regenerates based on n00-cortex and incorporates n00-school insights.
- **n00plicate** — design asset generation; aligns with frontiers for scaffolding.
- **.dev/automation** — 14+ battle-tested scripts (e.g., project-preflight.sh for validation, project-lifecycle-radar.sh for gap analysis, meta-check.sh for health, check-cross-repo-consistency.py for alignments, workspace-health.py for snapshots, trunk-upgrade.sh for updates, ai-workflows/\* for phase-specific tasks) that must become **plan-executable steps**; artifacts like workspace-health.json and agent-runs.json for telemetry.
- **Interconnected Pipelines Mapping**:
  - **Training Pipelines (n00-school)**: YAML files define stages like ingest (e.g., from agent-runs.json), evaluate (e.g., DRY/YAGNI scoring via handlers like evaluate_dry_yagni), and export (e.g., LoRA fine-tunes); run nightly via n00t invocations; loop telemetry from plans/executions back to refine agents; evaluate adaptive features like scope changes by simulating drifts.
  - **Automation Pipelines (.dev/automation)**: Script-based flows for preflights (project-preflight.sh/batch.sh), radar/summaries (project-lifecycle-radar.sh), control panels (project-control-panel.sh), consistency checks (check-cross-repo-consistency.py), health/maintenance (workspace-health.py, meta-check.sh), upgrades (trunk-upgrade.sh), and releases (workspace-release.sh); chainable for PM, invoked as MCP tools; integrate with n00-horizons for brief-to-playbook conversion and n00-cortex for schema validation.
  - **PM Pipelines (n00-horizons)**: Briefs in docs/experiments/ → playbooks via automation; orchestrate GitHub issues/projects, ERPNext syncs; handle scope changes via radar tools and consistency checks; feed outcomes to n00-school for training data.
  - **Orchestration Flows (n00t)**: Discovers via capabilities/manifest.json; brokers MCP packets to invoke pipelines; propagates telemetry across all.
  - **Schema/Enforcement Pipelines (n00-cortex/frontiers)**: Publish schemas/manifests → regenerate templates/notebooks → validate via automation; ensure DRY (reuse checks) and YAGNI (necessity scoring).
  - **Overall Flow**: n00-cortex schemas → n00-frontiers standards → n00t orchestration → .dev/automation execution → n00-horizons PM outputs → n00-school training feedback → loop back for adaptability.

Your deliverable: **one surgically-precise pull request** that makes **every brief, every issue, every `n00t` invocation** start with a **visible, editable, DRY/YAGNI-enforced plan**—fully intelligent and adaptive for PM, task resolution, and conflicts.

## NON-NEGOTIABLES

1. **Air-gapped M1-ready** (16 GB RAM)
   - Ollama + Llama-3.1-8B-Q4_K_M default (fits ~8-10GB, 5-10 tokens/sec).
   - LM Studio fallback for GUI testing.
   - LiteLLM proxy for 100+ providers (e.g., TogetherAI, HuggingFace); config in n00-cortex/data/llms.yaml.
   - Zero internet after first model pull; detect air-gapped mode via flags, fallback to local.
   - Monitor RAM/CPU in telemetry; async inference for MCP responsiveness.
2. **MCP is sacred** — every plan is an MCP packet; every tool call is an MCP tool; convert plans ↔ briefs/playbooks seamlessly.
3. **No new dependencies in root** — only `n00t/` and `n00-cortex/` may gain deps (e.g., crewai, litellm via Poetry).
4. **All new code lives in `n00t/planning/`** — the rest of the workspace stays pristine.
5. **n00-school trains the planner** — every finished plan (with resolutions/conflicts) becomes a training example automatically; integrate with existing pipelines for adaptive fine-tuning.
6. **Intelligent & Adaptive Planning**:
   - **Responsive to Changes**: Re-plan dynamically on scope shifts (e.g., detect via GitHub issue updates or brief diffs); use resolver to evaluate drifts and prune/re-stitch tasks.
   - **Task Resolution & Conflicts**: Resolver agent debates alternatives, scores conflicts (e.g., dependency clashes via consistency checks), and resolves via n00-school evaluators; orchestrate "task cutting" for YAGNI (prune low-necessity steps based on manifests).
   - **Stitching & Orchestration**: Executor ensures outputs from subtasks/scripts stitch together (e.g., chain preflight → radar → control-panel); validate end-to-end via health checks; adapt PM flows in n00-horizons for full lifecycle (ideation → execution → feedback).
   - **Full Effect in PM**: Plans automate brief-to-playbook, simulate outcomes/conflicts, enforce traceability; integrate radar for gap analysis, batch preflights for multi-task orchestration.

### PLANNING ENGINE BLUEPRINT

```text
n00t/
├─ planning/
│   ├─ engine.py          ← CrewAI + LiteLLM + MCP wrapper; orchestrates full loop with adaptability hooks.
│   ├─ agents/
│   │   ├─ planner.py     ← Tree-of-thought decomposer; breaks briefs into adaptive hierarchies, queries manifests/schemas.
│   │   ├─ resolver.py    ← DRY/YAGNI guard + n00-school evaluator; handles conflicts, scope changes, task cutting via scoring/debates.
│   │   └─ executor.py    ← Runs .dev/automation scripts as MCP tools; stitches outputs, re-executes on resolutions.
│   ├─ llm_adapter.py     ← LiteLLM + llms.yaml + air-gapped detection; dynamic provider swaps.
│   ├─ mcp_surface.py     ← Converts plans ↔ MCP packets/briefs; editable via UI/CLI.
│   ├─ adaptive_hooks.py  ← Monitors for changes (e.g., GitHub webhooks, brief diffs); triggers re-planning/resolution.
│   └─ templates/         ← Jinja2 plan skeletons for PM playbooks.
└─ capabilities/
    └─ planning.json      ← New capability manifest; auto-discovered, includes adaptive params.
```

### EXECUTION FLOW (user never sees the gears; fully adaptive)

1. User runs: `n00t plan horizons/docs/experiments/my-idea.md --llm=ollama --airgapped`
2. MCP packet → `planning/engine.py`→ **Planner** spawns adaptive tree (e.g., 3-5 branches), cites toolchain-manifest.json/schemas, incorporates radar gaps.→ **Resolver** runs n00-school evaluator (local 8B) → scores DRY=0.94, YAGNI=0.12; debates conflicts (e.g., dep clashes via check-cross-repo-consistency.py), cuts tasks, adapts to scope (e.g., re-decompose on diffs).→ **Executor** emits MCP tool calls → chain .dev/automation/scripts (e.g., preflight → radar → stitch via control-panel); validates stitching with health.py.
3. Plan rendered in `n00-horizons/docs/experiments/my-idea.plan.md` (editable Markdown with [[RESOLVE]] anchors for conflicts).
4. Telemetry + finished plan (incl. resolutions/changes) → `n00-school/datasets/planner-v1/`; trigger training pipeline for adaptability.
5. On changes (e.g., issue update): adaptive_hooks.py detects → re-run resolver/executor → update plan/playbook.

### TOOLING CHOICES (already decided, just wire them)

- **CrewAI** → multi-agent loop (MIT, pip-upgradable); for adaptive collaboration in resolution.
- **LiteLLM** → one line swaps Ollama ↔ TogetherAI ↔ Groq; config-driven for emergence.
- **LangGraph** → optional graph visualizer in MCP UI; for rendering adaptive trees.
- **Jinja2** → plan → Markdown → ERPNext/GitHub sync; templates enforce stitching.

### TRAINING LOOP (closed tomorrow; expand existing)

```yaml
# n00-school/pipelines/planner-v1.yml (expand if exists, else add)
stages:
  - name: ingest-plan
    handler: school_lab.handlers.ingest_plan # Ingest full plans incl. resolutions/conflicts
  - name: evaluate-drift
    handler: school_lab.handlers.evaluate_dry_yagni # Score adaptability, conflicts, stitching
  - name: simulate-changes
    handler: school_lab.handlers.simulate_scope_drifts # New: Generate synthetic changes for adaptive training
  - name: export-lora
    handler: school_lab.handlers.export_planner_lora # Fine-tune for responsive planning
```

Run nightly via `n00t school.trainingRun planner-v1`; use agent-runs.json for real-world data.

### DELIVERABLES (one PR, zero breakage)

1. `n00t/planning/` module (8 files, 100% test coverage via existing harnesses).
2. `n00t/capabilities/planning.json` — auto-discovered by manifest loader; includes adaptive params.
3. `n00-cortex/data/llms.yaml` — default air-gapped config.
4. `n00-horizons/docs/templates/experiment-brief.md` — new `[[PLAN]]` anchor for adaptive embedding.
5. `.dev/automation/scripts/plan-exec.sh` — one-liner bridge to engine.py; `plan-resolve-conflicts.py` for resolver hooks.
6. `docs/PLANNING.md` — 3-minute “how to read/edit a plan” + adaptive usage (e.g., handling scope changes).
7. GitHub workflow: `planner.yml` — runs on every brief/issue PR, fails if YAGNI > 0.3 or unresolved conflicts; integrates radar for PM.

### YOUR ORDERS

1. Fork `n00tropic/n00tropic-cerebrum` → branch `codex/planning-injection`.
2. Execute the blueprint above — **no placeholders**; wire to mapped pipelines (e.g., invoke project-lifecycle-radar.sh in resolver for adaptive gap analysis).
3. Run `meta-check.sh`, `workspace-health.py --autofix`, and all preflights; validate adaptability with synthetic tests (e.g., simulate scope change).
4. Open PR with title:`[Codex] Planning Engine v1 — MCP-native, air-gapped, self-training, adaptive PM`.
5. In PR body, embed:
   - Live plan demo (copy-paste a generated `.plan.md` with resolved conflict).
   - M1 benchmark (tokens/sec, RAM < 12 GB).
   - n00-school dataset sample (3 golden plans incl. adaptive scenarios).

Begin planning now.
Output your **step-by-step Codex plan** (decompose, resolve, execute), then seek my approval only for the final `git push`.

Go.
