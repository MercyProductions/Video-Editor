# Interactive Preview Mode

Interactive Preview Mode lets the editor create a playable review cache before final export. It uses the same JSON project and FFmpeg renderer as final output, but writes a temporary low-resolution MP4 plus review assets so users can inspect timing, captions, overlays, transitions, music, and safe-zone framing without committing to the final render.

## CLI

```powershell
python render.py interactive-preview examples/project.json -o output/interactive_preview --quality-mode balanced
```

Preview one scene only:

```powershell
python render.py interactive-preview examples/project.json -o output/interactive_preview_scene --quality-mode draft --scope scene --scene-id intro
```

Quality modes:

- `draft`: fastest, low-resolution preview.
- `proxy`: proxy-friendly preview.
- `balanced`: default review quality.
- `high`: sharper preview for text and motion checks.
- `final_sim`: slower render using final project size and timing.

## Outputs

The command writes:

- `interactive_preview.json`: preview metadata for the UI.
- `.interactive_cache/*.mp4`: playable cached preview video.
- `timeline_summary.json`: scenes, assets, duration, and missing assets.
- `render_plan.txt`: readable render plan.
- `scene_thumbnails/*.png`: scene preview thumbnails.
- `waveform.png`: audio waveform when music/audio exists.

## Desktop Controls

The Preview tab supports:

- play, pause, stop, resume, restart
- full timeline or selected-scene preview
- timeline scrubber and scene jumping
- playback speed control
- frame stepping
- mute, volume, and loop
- safe-zone overlays
- scene thumbnails
- waveform display
- preview quality modes
- cached representative frame generation

The preview cache is safe to delete. It is regenerated when project JSON, selected scope, scene, or quality mode changes.
