# Beginner Auto-Template Mode

Beginner Auto-Template Mode lets a non-technical user create a polished video without opening JSON. The app still generates `project.json` behind the scenes, and Advanced Mode can open that JSON at any time.

## Desktop Flow

1. Click **New Auto Video**.
2. Pick one or more sources:
   - video file
   - image folder
   - product asset folder
   - optional music
   - optional logo
3. Choose a premium template.
4. Enter product name, goal, key features, desired vibe, duration, and target platform.
5. Click **Generate Preview**.
6. Review the rendered preview and open Advanced Mode only if manual JSON or timeline edits are needed.
7. Click **Render Final MP4** when ready.

## CLI

List templates:

```powershell
python render.py auto-template list
python render.py auto-template list --json
```

Generate a preview render:

```powershell
python render.py auto-template create `
  --media examples/assets/gameplay.mp4 `
  --music examples/assets/beat_music.wav `
  --logo examples/assets/logo.png `
  --template premium_product_showcase `
  --product-name "Automatic Troubleshooter" `
  --goal "Show how it scans launch blockers and fixes common setup problems." `
  --feature "Missing runtimes" `
  --feature "Anti-cheat conflicts" `
  --feature "Windows security settings" `
  --vibe "premium red black cinematic" `
  --duration 12 `
  -o examples/generated/beginner_auto_template `
  --render --quality preview --cache
```

## Templates

- Premium Product Showcase
- YouTube Short
- TikTok/Reels Edit
- Software Demo
- Cybersecurity Tool Showcase
- Gaming Montage
- Tutorial Walkthrough
- Minimal SaaS Promo
- Cinematic Trailer
- Before/After Reveal

Each template defines aspect ratio, pacing, caption style, intro/outro style, transition behavior, lighting/color behavior, title card format, default scene structure, and export settings.

## Outputs

The generated folder includes:

- `project.json`
- `content_brief.json`
- `script.json`
- `scene_plan.json`
- `content_plan.json`
- `generation_review.json`
- `review_summary.txt`
- `beginner_auto_template_summary.json`
- preview reports
- `final_video.mp4` when rendering is enabled

## Design Rule

JSON remains the editing source of truth. Beginner Mode hides it by default; Advanced Mode exposes it for power users.
