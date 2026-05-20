# Autonomous Production Pipeline

Autonomous Production Pipeline Mode runs a local, creator-controlled workflow from idea to reviewable edit:

`idea -> planning -> scripting -> scene generation -> editing -> review -> export package`

It does not replace `project.json`. The generated JSON remains the source of truth, and final rendering/package creation is gated by explicit creator approval.

## CLI

```powershell
python render.py autonomous "Create a 35 second premium red black showcase for my automatic troubleshooter. It scans missing runtimes, launch blockers, anti-cheat conflicts, and Windows security settings." --assets examples/assets --music examples/assets/beat_music.wav --logo examples/assets/logo.png --platform shorts --content-type product_showcase --vibe "premium red black cinematic" --render-preview --cache -o examples/generated/autonomous_troubleshooter
```

To allow a final render and posting package after review:

```powershell
python render.py autonomous "Create a 35 second premium red black showcase for my automatic troubleshooter." --assets examples/assets --music examples/assets/beat_music.wav --approved --final-render --package --quality final -o examples/generated/autonomous_troubleshooter_final
```

## Outputs

The mode writes:

- `autonomous_plan.json`: structure, pacing, reveal timing, CTA placement, style direction, asset rules, and approval policy.
- `content_brief.json`, `script.json`, `scene_plan.json`, `content_plan.json`: generated content plan from the existing content generator.
- `generation_review.json`, `approval_state.json`, `review_summary.txt`: human review packet.
- `project.json`: renderable project JSON.
- `preview_video.mp4`: low-risk preview render when `--render-preview` is used.
- `autonomous_asset_selection.json`: selected clips, highlight timings, tags, and selection reasons.
- `autonomous_quality_review.json`: quality check, preflight, readiness score, warnings, and blocking issues.
- `autonomous_variants.json`: hook, pacing, CTA, thumbnail, and platform project variants.
- `autonomous_explainability.json` and `.txt`: why the AI chose the structure, style, clips, pacing, and effects.
- `upload_package/`: only when `--approved --final-render --package` are used.

## Human Approval Layer

Preview generation is allowed before approval so the creator can review the edit. Final render/package work requires `--approved`.

The creator can still use the existing review commands:

```powershell
python render.py content-review show examples/generated/autonomous_troubleshooter/content_plan.json
python render.py content-review approve examples/generated/autonomous_troubleshooter/content_plan.json --section all --status approved
```

## Design Notes

- Local-first: no accounts, telemetry, cloud rendering, or remote services.
- Non-destructive: source media is referenced; trims and effects live in JSON.
- Explainable: every autonomous pass writes the decision summary.
- Modular: the pipeline composes the existing generator, renderer, preflight, thumbnails, variants, and posting package systems.
