# Proactive Creative Assistance

Proactive Creative Assistance turns the desktop app into an active local production partner. It watches the current project JSON, preview state, render queue, and adaptive workflow memory, then surfaces useful suggestions before the creator asks for them.

## Local-Only Inputs

The assistant analyzes:

- timeline scene durations
- caption length and reading speed
- repeated transitions
- layer density and visual overload risk
- render queue failures
- cache/proxy state
- platform preset
- adaptive workflow memory
- current project metadata

No cloud service, telemetry, account, or remote model is required.

## Suggestion Types

The right-rail Proactive Assistant panel groups work into:

- workflow suggestions, such as stronger hooks or smoother transitions
- predictive issues, such as fast captions, pacing drops, dead sections, or visual overload
- optimization suggestions, such as enabling proxies/cache for large edits
- creative opportunities, such as thumbnail candidates, reveal moments, and high-energy sections
- creator coaching, such as Shorts intro timing or tutorial readability guidance

## One-Click Actions

Suggestions can apply safe, metadata-only edits:

- shorten an intro scene with ripple timing
- mark a weak scene for review
- smooth repeated transitions
- slow captions through the existing assistant instruction path
- reduce excessive motion
- enable proxy preview/cache
- jump the preview playhead to a thumbnail or reveal moment

Source media remains untouched.

## Background Improvement Queue

When the app is idle, it prepares lightweight alternatives without interrupting the creator:

- alternate hooks
- cleaner caption variants
- tighter pacing candidates
- thumbnail moments

The creator can apply or skip each item. Nothing is silently committed.

## Verification

```powershell
cd C:\Users\gabri\Desktop\Aegis\Tools\Kioson\automatic-video-editor\desktop-app
npm run typecheck
npm run build
```

Renderer smoke check:

```powershell
cd C:\Users\gabri\Desktop\Aegis\Tools\Kioson\automatic-video-editor
python render.py render examples/project.json -o output/proactive_assistance_verify.mp4 --quality preview --cache
```
