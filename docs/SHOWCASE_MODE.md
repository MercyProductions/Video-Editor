# Cinematic Auto Showcase Mode

Showcase Mode turns one raw desktop recording into a polished trailer-style edit while keeping JSON as the source of truth.

It analyzes:

- motion and focus regions
- click-like interaction spikes
- window or scene changes
- idle/dead moments
- text-heavy moments
- active-window, modal, menu, status-message, button/control, and brand-area candidates
- cursor intent: hover, search movement, action clicks, drag sequences, idle cursor
- optional music beats, peaks, and bass drops

Generate a project JSON:

```powershell
python render.py showcase raw_recording.mp4 --style auto --instructions "Make this feel like a premium cybersecurity tool" -o examples/generated/showcase_project.json
```

Generate and render:

```powershell
python render.py showcase raw_recording.mp4 --music music.wav --logo logo.png --style hacker_cyber --product-name "Aegis Troubleshooter" --duration 30 -o examples/generated/showcase_project.json --analysis-output output/showcase_analysis.json --render --render-output output/showcase_preview.mp4 --quality preview
```

Use natural-language instructions:

```powershell
python render.py showcase raw_recording.mp4 --instructions "Make this a 45-second premium red/black cybersecurity showcase. Use smooth zooms, subtle glow, dark lighting, no loud effects, and focus on the login, dashboard, and scan results." -o examples/generated/showcase_project.json
```

The interpreter writes a structured local spec containing style, target duration, lighting, focus targets, cut-out requests, audio behavior, title-card direction, and reasoning:

```powershell
python render.py showcase raw_recording.mp4 --instructions "Focus on login, dashboard, and scan results" --spec-output output/showcase_spec.json
```

List presets:

```powershell
python render.py showcase --list-styles
```

Built-in showcase styles:

- `cinematic_tech_trailer`
- `premium_saas_showcase`
- `hacker_cyber`
- `gaming_product_showcase`
- `luxury_ui_reveal`
- `minimalist_product_reveal`

Custom style profile example:

```json
{
  "style": "premium_tech",
  "lighting": "soft_red_glow",
  "cameraMovement": "smooth",
  "pace": "medium_fast",
  "transitionIntensity": 0.6,
  "zoomAggressiveness": 0.35
}
```

Use it with:

```powershell
python render.py showcase raw_recording.mp4 --style-profile style.json -o examples/generated/showcase_project.json
```

Manual override JSON:

```json
{
  "mustShow": ["login screen", "dashboard", "scan results"],
  "cutOut": ["desktop idle", "file explorer"],
  "style": "premium cyber",
  "duration": 45,
  "musicSync": true,
  "lighting": {
    "theme": "red_black",
    "intensity": 0.45
  }
}
```

Use it with:

```powershell
python render.py showcase raw_recording.mp4 --overrides examples/showcase_overrides.json --score-output output/showcase_score.json
```

Outputs:

- project JSON with intro, feature scenes, outro, captions, focus crops, camera movement, lighting, and transitions
- desktop analysis JSON
- structured specification JSON
- showcase score JSON for pacing, readability, focus clarity, dead time, lighting, transitions, and brand consistency
- optional rendered MP4

The generated project remains editable in Advanced Mode and can be rendered with the normal `render` command.
