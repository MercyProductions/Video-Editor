# Product Engineering Charter

This project is now past broad feature expansion. Future work should improve reliability, polish, performance, cinematic quality, and workflow trust before adding new surface area.

## Development Philosophy

- Stable over flashy.
- Fast over overengineered.
- Reliable over experimental.
- Cohesive over bloated.
- Local-first always.
- JSON remains the editing backbone.
- Deterministic behavior is preferred whenever practical.
- AI assists the creator; it does not remove creator control.

## Feature Gate

Every future feature or major change must justify:

- Creator value: the workflow problem it solves.
- Performance cost: render time, preview time, startup time, and task latency.
- Memory cost: RAM, VRAM, cache growth, and large-project behavior.
- UI complexity: new screens, controls, states, and beginner/advanced mode impact.
- Render complexity: FFmpeg graph impact, cache invalidation, determinism, and failure modes.
- Maintenance burden: tests, docs, ownership, API stability, and long-term debugging.
- Scalability: how it behaves on large projects, many assets, and long renders.

If the justification is weak, improve an existing workflow instead.

## Current Focus Areas

### Rendering Quality

- Smoother motion.
- Cleaner transitions.
- Better pacing.
- Cinematic consistency.
- Audio polish.

### Stability

- Crash recovery.
- Autosaves.
- Memory management.
- Deterministic exports.
- Corruption resistance.

### Workflow Speed

- Proxy performance.
- Cache reuse.
- Timeline responsiveness.
- Background worker reliability.

### AI Quality

- Better scene understanding.
- Smarter pacing.
- Stronger cinematic direction.
- Fewer bad edits.
- Clearer explanations.
- Creator identity preservation.

### User Experience

- Cleaner UI.
- Fewer clicks.
- Predictable behavior.
- Creator control.
- Better previews.

## Long-Term Evolution Operating Model

The product should evolve as a unified local-first creative production platform, not as a pile of disconnected editing tools. When work spans multiple areas, route it through the existing source-of-truth systems:

- `project.json` for edit state.
- Local asset database for media intelligence.
- Workflow profiles and pipelines for repeatability.
- Feedback reviews and creator identity for personalization.
- Render reports, quality checks, and evolution reports for trust.

The AI assistant should behave as a planner, editor, pacing assistant, showcase director, workflow helper, and production assistant, but every AI change must remain explainable, reviewable, and reversible.

Before large changes, run:

```powershell
python render.py evolution-report --project examples/project.json --profile "Default Creator" -o output/long_term_evolution_report.json
```

Use the report's next actions to favor refinement, workflow smoothness, stability, cinematic quality, and creator trust over new surface area.

## Vertical Build Rule

Build vertical improvements that start and end in a real workflow:

1. Import or open a real project.
2. Make the smallest meaningful improvement.
3. Validate the JSON.
4. Preview or render a real MP4 when rendering behavior changes.
5. Measure or document the before/after.
6. Update docs only where they help future work.

Avoid horizontal scaffolding unless it is immediately used by a working path.

## Real-World Test Set

Use actual creator workflows when testing changes:

- Desktop showcases.
- Gaming clips.
- Software demos.
- Cybersecurity tool showcases.
- Tutorial recordings.
- Cinematic trailers.
- TikTok edits.
- YouTube intros.

At least one relevant workflow should be exercised before considering a change done.

## Refactor Standard

Refactor aggressively when systems become messy, but keep refactors honest:

- Preserve runnable commands.
- Preserve project JSON compatibility unless migration is explicit.
- Keep source media non-destructive.
- Keep local-first behavior intact.
- Keep CLI workflows working even when UI changes.
- Prefer deleting dead code over wrapping it in more abstraction.

## Done Definition

A change is done when:

- It compiles.
- It validates or renders through the affected workflow.
- It does not make beginner workflows harder.
- It keeps advanced control available where relevant.
- It has clear failure behavior.
- It is documented if future maintainers need to know it exists.
