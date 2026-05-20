# Final Review Preflight

Final Review Preflight runs before final export to catch issues that would waste render time or create a weak upload package. It is local-only and reads the project JSON plus the approved preview video when available.

## CLI

```powershell
python render.py final-preflight check examples/project.json -o output/final_preflight.json --format mp4
```

With an approved preview video:

```powershell
python render.py final-preflight check examples/project.json --preview-video output/interactive_preview/.interactive_cache/preview.mp4 -o output/final_preflight.json
```

Apply all safe repairs:

```powershell
python render.py final-preflight repair examples/project.json -o output/project.preflight_repaired.json --mode all
```

Accept one issue:

```powershell
python render.py final-preflight repair examples/project.json -o output/project.accepted.json --mode ignore --issue-id ISSUE_ID
```

## Checks

Preflight checks:

- missing assets and undefined references
- broken media
- unresolved preview review markers
- unapproved scenes
- audio timing and dead silence
- caption speed and caption bounds
- text safe zones
- contrast/readability
- aggressive flashing or motion effects
- black/frozen frames in the approved preview
- export preset/format mismatch

## Repair Actions

Safe one-click repairs can:

- adjust caption timing
- move text into the safe zone
- lower effect intensity
- normalize audio timing and volume defaults
- replace harsh transitions with safer crossfades

Unsafe issues, such as missing assets or unapproved scenes, require user review or explicit acceptance.

## Readiness

The report includes:

- pacing score
- readability score
- audio score
- brand consistency score
- technical readiness score
- final export summary with platform, resolution, duration, FPS, codec, bitrate, caption status, thumbnail status, and warnings remaining
