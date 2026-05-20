# Content Generator Mode

Content Generator Mode creates a complete short-form video structure from an idea, product info, raw notes, optional footage, optional logo, and optional music. It remains local-first and writes normal project JSON as the source of truth.

## Command

```powershell
python render.py content-generate "Create a YouTube Short for Automatic Troubleshooter with runtime scans, launch blocker detection, anti-cheat checks, and Windows security fixes" --mode youtube_shorts --product-name "Automatic Troubleshooter" --assets examples/assets --music examples/assets/beat_music.wav --logo examples/assets/logo.png --duration 15 --tone cinematic -o examples/generated/content_generator_rendered --render --quality preview --cache
```

## Modes

- `youtube_shorts`: vertical 1080x1920, strong hook, fast pacing, large captions, CTA ending.
- `tiktok`: vertical 1080x1920, trend-style pacing, punchy captions, faster cuts.
- `product_showcase`: cinematic intro, feature reveals, smooth zooms, clean title cards.
- `tutorial`: step-by-step scenes, readable captions, slower pacing, clear focus.
- `promo_ad`: problem/solution structure, benefit-driven copy, polished CTA.

## Inputs

- `idea`: raw prompt, notes, or product description.
- `--product-name`: product name override.
- `--platform`: `shorts`, `tiktok`, `youtube`, `square`, or related aliases.
- `--goal`: specific video goal.
- `--bullet`: feature or note, repeatable.
- `--assets`: folder of raw clips/images.
- `--music`: optional local music track.
- `--logo`: optional local logo.
- `--duration`: desired seconds.
- `--tone`: `minimal`, `cinematic`, `aggressive`, or `clean`.
- `--style`: `auto` or a named style preset.

## Outputs

The output folder contains:

- `content_brief.json`
- `script.json`
- `scene_plan.json`
- `content_plan.json`
- `generation_review.json`
- `approval_state.json`
- `ai_reasoning_summary.txt`
- `review_summary.txt`
- `project.json`
- `preview/timeline_summary.json`
- `preview/render_plan.txt`
- `content_generation_summary.json`
- `final_video.mp4` when `--render` is used

## Regeneration And Locks

Regenerate only the script while preserving existing scene structure:

```powershell
python render.py content-generate "Make this cleaner and more tutorial-like" --mode tutorial --existing-plan examples/generated/content_generator_tutorial/content_plan.json --regenerate script --lock scene:step_1 -o examples/generated/content_generator_regen_script
```

Supported regeneration scopes:

- `--regenerate full`
- `--regenerate none`
- `--regenerate hook`
- `--regenerate script`
- `--regenerate captions`
- `--regenerate scenes`
- `--regenerate scene_plan`
- `--regenerate style`

Supported locks:

- `--lock hook`
- `--lock script`
- `--lock script:<index>`
- `--lock style`
- `--lock music`
- `--lock scene:<scene_id>`
- `--lock caption:<scene_id>`
- `--lock timing:<scene_id>`
- `--lock title:<scene_id>`

## Review Before Render

The generator always writes `review_summary.txt`, `generation_review.json`, `approval_state.json`, and `ai_reasoning_summary.txt` before final export. Review the hook, script, scene plan, captions, style, reasoning, and warnings before final export.

```powershell
python render.py content-review show examples/generated/content_generator_rendered/content_plan.json
python render.py content-review approve examples/generated/content_generator_rendered/content_plan.json --section all --status approved
```

Final-quality renders are blocked until all generated sections are approved or locked. Preview-quality renders are still available for review.

```powershell
python render.py content-review compare examples/generated/content_generator_rendered/content_plan.json examples/generated/content_generator_regen_script/content_plan.json -o examples/generated/content_generator_compare
```
