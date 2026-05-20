# JSON Schema Reference

Schema file:

`src/schema/project.schema.json`

Top-level fields:

- `project`: width, height, fps, duration, background, optional crf/export preset.
- `assets`: map of local asset keys to paths.
- `timeline`: ordered list of scenes.
- `audio`: optional audio tracks.
- `captions`: optional global captions.
- `metadata`: local project intelligence, timeline markers, workflow notes, and non-rendering metadata.

Renderable layer types:

- `video`
- `image`
- `text`
- `caption`
- `captions`
- `solid`
- `shape`
- `progress`
- `lower_third`
- `hud`
- `animated_background`
- `particle`
- `waveform`

Validation:

```powershell
python render.py validate examples/project.json
python render.py repair examples/bad_project.json -o examples/generated/repaired.json
```

Generated JSON must validate before render. Repair may fill safe defaults, but it should not be used as a substitute for clear template definitions.
