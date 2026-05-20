# MVP Roadmap

This roadmap cuts the product back to a buildable local-first path. Every version must compile, validate JSON, and render a real MP4 with FFmpeg before the next version starts.

## Product Rules

- JSON remains the source of truth.
- FFmpeg is the renderer until the basic workflow is stable.
- Everything works offline and local-first.
- No cloud accounts, telemetry, marketplace, or remote rendering.
- No advanced systems until the basic import -> JSON -> render loop is reliable.
- Each milestone must include a smoke project, a render command, and a produced MP4.

## Actual MVP Folder Structure

```text
automatic-video-editor/
  render.py
  requirements.txt
  src/
    main.py                  # CLI entry point
    parser/                  # project JSON parsing into runtime models
    schema/                  # project.schema.json and validator
    assets/                  # asset resolution and missing-asset checks
    renderer/                # FFmpeg scene/audio/render pipeline
    effects/                 # text, video, graphics, effect graph filters
    transitions/             # cut, crossfade, fade, slide, zoom transitions
    reports/                 # render reports
    mvp/                     # executable milestone helpers, starting with quick-create
    intelligence/            # starts in 0.2 with beat/analysis helpers
    repair/                  # starts in 0.3
    templates/               # starts in 0.3
    recovery/                # starts in 0.3 autosave
    showcase/                # starts in 0.5
  examples/
    project.json             # 0.1 smoke project
    assets/                  # local sample clips/images/music
    generated/               # generated project JSON
  output/                    # rendered videos and reports
  desktop-app/               # starts in 0.4
  docs/
    MVP_ROADMAP.md
    mvp/
      VERSION_0_1_IMPLEMENTATION_PLAN.md
```

## MVP 0.1 - Core Render Pipeline

Goal: one MP4 desktop recording plus optional music and text instructions can produce project JSON and a rendered edited MP4.

Must include:
- Import one MP4 desktop recording.
- Import optional music.
- Enter style instructions as simple CLI fields or JSON metadata.
- Generate or load project JSON.
- Render edited MP4 with FFmpeg.
- Simple cuts.
- Simple zooms.
- Title cards.
- Basic color grading.
- Basic captions/manual text.

Definition of done:
- `python render.py validate examples/project.json` passes.
- `python render.py render examples/project.json -o output/mvp_0_1.mp4 --quality preview` creates a playable MP4.
- `python render.py quick-create ... --render` creates a project JSON and playable MP4 from one input MP4.
- Bad JSON shows a clear schema error.
- Missing assets show clear asset errors.

## MVP 0.2 - Desktop Analysis

Goal: desktop recordings become cleaner automatically.

Add:
- Desktop footage analysis.
- Cursor/click detection using local frame-difference heuristics.
- Dead-time trimming recommendations.
- Focus-region zooms.
- Music beat sync.
- Render report.

Definition of done:
- A raw desktop recording can generate an analysis JSON.
- The generated project avoids or shortens obvious idle sections.
- Focus crops and zooms are visible in the rendered MP4.
- Render report lists duration, assets, warnings, output size, and render time.

## MVP 0.3 - Local Generation Helpers

Goal: users can generate and repair JSON without hand-editing every field.

Add:
- Local AI prompt-to-JSON path, with deterministic fallback templates when no model is available.
- JSON repair.
- Templates.
- Preview render.
- Export presets.
- Project autosave.

Definition of done:
- Prompt-to-JSON creates valid project JSON without cloud APIs.
- Repair can fix common missing project fields.
- At least three templates render to MP4.
- Preview render is faster/lower quality than final render.
- Autosave writes recoverable JSON snapshots.

## MVP 0.4 - Desktop App Shell

Goal: the engine becomes usable without living in the terminal.

Add:
- Electron/React UI.
- Timeline preview.
- Asset library.
- Render queue.
- Settings page.
- Local model manager.

Definition of done:
- App launches locally.
- User can open project JSON.
- User can render via UI and see logs/progress.
- User can preview timeline structure.
- CLI remains fully usable.

## MVP 0.5 - Controlled Intelligence

Goal: showcase generation becomes useful without hiding creator control.

Add:
- Cinematic showcase mode.
- AI director suggestions.
- Scene scoring.
- Local project database.
- Plugin-ready architecture.

Definition of done:
- One raw desktop recording can generate a showcase project and preview MP4.
- Every AI suggestion includes a reason and confidence.
- User can lock or preserve scenes before regeneration.
- Local database indexes assets and usage without telemetry.
- Plugin loading is local-folder only and isolated behind explicit warnings.

## Stop Conditions

Do not start the next version until:
- Current milestone render smoke test passes.
- Current milestone checklist is complete.
- README command examples work.
- The newest code path has at least one generated MP4 in `output/`.
- New complexity is justified by workflow speed, render quality, stability, or creator control.
