# Content Review Workflow

Content Generator Mode now creates a reviewable plan before final export. The JSON project remains the source of truth, but the generated script, scenes, captions, style, reasoning, and approval state are written separately so the creator can approve or regenerate specific sections.

## Generate A Review Plan

```powershell
python render.py content-generate "Create a YouTube Short for Automatic Troubleshooter with runtime scans and Windows security fixes" --mode youtube_shorts --product-name "Automatic Troubleshooter" --duration 15 -o examples/generated/review_plan
```

Outputs:

- `content_plan.json`: structured generation plan.
- `generation_review.json`: hook, script, scenes, captions, style, assets, warnings, and section statuses.
- `approval_state.json`: final-render readiness.
- `ai_reasoning_summary.txt`: why the hook, scene order, style, and footage were chosen.
- `version_comparison.json` / `.md`: written when regenerating from an existing plan.
- `project.json`: validated renderable project JSON.

## Review And Approve

```powershell
python render.py content-review show examples/generated/review_plan/content_plan.json
python render.py content-review approve examples/generated/review_plan/content_plan.json --section all --status approved
```

Sections can be approved, locked, rejected, or returned to `needs_review`.

Examples:

```powershell
python render.py content-review approve examples/generated/review_plan/content_plan.json --section hook --status approved
python render.py content-review approve examples/generated/review_plan/content_plan.json --section scene:feature_1 --status locked
python render.py content-review approve examples/generated/review_plan/content_plan.json --section caption:cta --status rejected
```

## Targeted Regeneration

Regenerate only the part that needs work while preserving locked sections:

```powershell
python render.py content-generate "Make the captions clearer and less hype-heavy" --mode youtube_shorts --existing-plan examples/generated/review_plan/content_plan.json --regenerate captions --lock scene:problem -o examples/generated/review_plan_captions_v2
```

Supported regeneration targets:

- `hook`
- `script`
- `captions`
- `scenes`
- `scene_plan`
- `style`
- `full`

Supported lock keys:

- `hook`
- `script`
- `script:<index>`
- `style`
- `music`
- `scene:<id>`
- `caption:<id>`
- `timing:<id>`
- `title:<id>`

## Compare Versions

```powershell
python render.py content-review compare examples/generated/review_plan/content_plan.json examples/generated/review_plan_captions_v2/content_plan.json -o examples/generated/review_compare
```

The comparison includes script diff, scene-plan diff, JSON diff, and optional render paths for side-by-side review.

## Final Render Gate

Preview-quality renders can be generated for review. Final-quality renders are blocked until all generated sections are approved or locked:

```powershell
python render.py content-generate "Render the approved short" --mode youtube_shorts --existing-plan examples/generated/review_plan/content_plan.json --regenerate none --approved --render --quality final -o examples/generated/review_final
```

The desktop app exposes the same flow in the AI Panel: generate a Content Mode plan, inspect the Generation Review card, lock sections, regenerate hook/captions/scenes/style, approve the plan, then render.
