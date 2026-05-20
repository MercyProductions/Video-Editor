# Long-Term Evolution

The long-term evolution phase is not a feature expansion phase. It is a quality, trust, and cohesion phase for turning the editor into a unified local-first creative production platform.

## Core Rule

Improve real workflows before adding new systems.

Every future feature must justify:

- Real creator value.
- Workflow improvement.
- Performance cost.
- Memory cost.
- UI complexity.
- Render complexity.
- Maintenance burden.
- Long-term scalability.

## Evolution Report

Generate the local evolution report:

```powershell
python render.py evolution-report --project examples/generated/phase17_identity_workflow_batch/v01_serious_cinematic/project.json --profile "Aegis Creator" -o output/long_term_evolution_report.json
```

Include the release gate when preparing a candidate build:

```powershell
python render.py evolution-report --project examples/generated/phase17_identity_workflow_batch/v01_serious_cinematic/project.json --profile "Aegis Creator" --include-release-check -o output/long_term_evolution_release_report.json
```

The report aggregates:

- Product philosophy and controlled-expansion gate.
- Unified creative workspace surface.
- Modular engine registry and architecture audit.
- Project quality, pacing, captions, motion intensity, style consistency, and hook strength.
- Creator identity and generation guidance.
- Workflow dashboard, render queue state, asset database health, cache/storage, and metrics.
- Local AI status and fallback behavior.
- Maintainability warnings and next actions.

## Desktop Workflow

In the desktop app, open the Product tab and use the Long-Term Evolution panel. It refreshes the same local report and shows:

- Readiness score.
- Local-first status.
- Documentation count.
- Architecture warning count.
- Current project intelligence availability.
- Recommended next actions.

## What This Prevents

- Feature bloat without workflow proof.
- Generic AI edits that ignore creator identity.
- UI surface area that beginners cannot understand.
- Renderer changes that are hard to debug.
- Cache, preview, or render regressions that only show up late.
- Architecture drift away from local-first ownership.

## What This Enables

- One cohesive creative workspace.
- A controllable local AI assistant.
- Projects that accumulate useful intelligence.
- Stable engine boundaries.
- Faster refinement cycles.
- Explainable evolution over time.

## Done Definition For Future Work

A change is not done until:

- It compiles.
- It validates or renders a real workflow.
- It preserves local-first behavior.
- It keeps JSON as the source of truth.
- It has predictable failure behavior.
- It updates docs only where future maintainers benefit.
