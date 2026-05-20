# MVP 0.1 Implementation Plan

Version 0.1 is the smallest honest product: import one desktop MP4, optionally add music, generate or load project JSON, and render a polished-enough edited MP4 with FFmpeg.

## Scope

In scope:
- MP4 video input.
- Optional music input.
- Project JSON validation.
- Asset loading and missing-file errors.
- Text/title/caption overlays.
- Simple video trims.
- Simple cuts and crossfades.
- Simple zoom/crop behavior.
- Basic color grade using FFmpeg filters.
- Final MP4 export.

Out of scope:
- Electron UI.
- Local LLM integration.
- Desktop semantic understanding.
- Plugin SDK.
- GPU render graph.
- Database indexing.
- Marketplace or cloud anything.

## Owned Folders

```text
src/main.py              # render and validate commands only
src/mvp/                 # quick-create executable milestone path
src/parser/              # JSON -> ProjectConfig
src/schema/              # schema validation
src/assets/              # local asset resolution
src/renderer/            # FFmpeg render pipeline
src/effects/             # text/video effects used by renderer
src/transitions/         # simple scene transitions
src/reports/             # basic render report
examples/project.json    # smoke project
examples/assets/         # sample local media
output/                  # generated MP4
```

## Checklist

- [ ] Confirm `python render.py validate examples/project.json` passes.
- [ ] Confirm missing video asset produces a readable error.
- [ ] Confirm missing music asset produces a readable error.
- [ ] Render a video-only MP4.
- [ ] Render a video + music MP4.
- [ ] Render a title-card scene.
- [ ] Render a manual caption/text overlay.
- [ ] Render a trimmed source video clip.
- [ ] Render a simple zoom/crop.
- [ ] Render a crossfade or cut transition.
- [ ] Render basic color grading.
- [ ] Generate `output/mvp_0_1.mp4`.
- [ ] Generate project JSON and MP4 with `quick-create`.
- [ ] Generate a render report next to the output.
- [ ] Document the exact smoke command in README.

## First Vertical Slice

1. Validate `examples/project.json`.
2. Parse settings, assets, timeline, audio.
3. Render each scene to temp MP4.
4. Apply simple transition joining.
5. Mix optional music with fades and volume.
6. Mux video/audio to final MP4.
7. Write render report.
8. Re-run validation and render after every renderer change.

## Smoke Commands

```powershell
python render.py validate examples/project.json
python render.py render examples/project.json -o output/mvp_0_1.mp4 --quality preview --cache
python render.py quick-create examples/assets/gameplay.mp4 --music examples/assets/beat_music.wav --logo examples/assets/logo.png --title "Aegis Troubleshooter" --caption "Scans runtimes, launch blockers, anti-cheat conflicts, and Windows security settings." --style red_black --duration 8 -o examples/generated/mvp_0_1_quick_create.json --render --render-output output/mvp_0_1_quick_create.mp4 --quality preview --cache
```

Expected result:

```text
output/mvp_0_1.mp4
output/mvp_0_1_quick_create.mp4
output/render_report.json
```

## Acceptance Criteria

- The MP4 opens in a normal video player.
- Output duration is within 0.25 seconds of project duration.
- Text is visible and not clipped.
- Audio is audible and does not obviously desync.
- JSON remains editable after render.
- Source media is never modified.
- The code path remains simple enough to debug in one sitting.
