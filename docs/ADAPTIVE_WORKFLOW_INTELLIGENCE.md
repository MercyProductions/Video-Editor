# Adaptive Workflow Intelligence

Adaptive Workflow Intelligence makes the desktop app feel familiar over time without sending any data off the machine.

## What It Learns

The app records small local workflow events:

- preferred beginner templates
- target platforms and export presets
- typical video duration
- pacing and caption density
- motion intensity and transition behavior
- hook style
- approved styles
- repeated corrections such as slower captions, milder zooms, or different transition timing
- failed exports and slow operations from the local friction log

The JSON renderer remains the source of truth. Adaptive memory only preselects UI defaults and creates suggestions.

## Local Storage

Electron stores the memory file in the app user-data folder:

```text
adaptive-workflow-memory.json
```

The file is local-only, capped to recent events, and written transactionally through a temporary file before replacement.

## Smart Defaults

Beginner Mode can apply learned defaults for:

- template
- target platform
- export preset
- aspect ratio
- caption density
- caption size
- pacing
- transition type and intensity
- lighting profile
- duration
- audio normalization target

Defaults only nudge the workflow. The user can still choose a different template, preset, caption style, or duration.

## Context-Aware Suggestions

When media or prompt text suggests a workflow, the app shows suggestions:

- desktop recordings -> software showcase mode
- gameplay -> gaming montage mode
- talking-head content -> caption-heavy mode
- tutorial language -> clarity mode

Repeated user corrections become recovery rules. For example, if the creator keeps slowing captions, future suggestions prefer less dense captions.

## UI Surfaces

Beginner Mode shows an Adaptive Workflow Intelligence card with current smart defaults and top suggestions.

The Product pane shows:

- event count
- preferred template and export preset
- learned duration
- creator fingerprint
- recovery rules
- friction summary
- repeated corrections

## Verification

Run the desktop checks:

```powershell
cd C:\Users\gabri\Desktop\Aegis\Tools\Kioson\automatic-video-editor\desktop-app
npm run typecheck
npm run build
```

Run renderer checks:

```powershell
cd C:\Users\gabri\Desktop\Aegis\Tools\Kioson\automatic-video-editor
python -m compileall src
python render.py render examples/project.json -o output/adaptive_workflow_verify.mp4 --quality preview --cache
```
