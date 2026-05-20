# JSON Guide

The project JSON is the source of truth. A valid project defines project settings, assets, timeline scenes, optional captions, optional audio, and an export preset.

Required core fields:

- `project.width`, `project.height`, `project.fps`, `project.duration`, `project.background`
- `assets` as a map of asset keys to local paths
- `timeline` as a list of scenes with `id`, `start`, `duration`, and `layers`

Layer types supported by the renderer include `video`, `image`, `text`, `caption`, `captions`, and `solid`. Source files are never modified; trims, color, speed, captions, and effects are render-time metadata.

Run:

```powershell
python render.py validate examples/project.json
python render.py repair examples/project.json -o examples/generated/repaired.json
python render.py render examples/project.json -o output/final_video.mp4
```
