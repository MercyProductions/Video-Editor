# Workflow Friction Reduction

This phase keeps the product local-first while reducing the number of decisions a creator has to make before seeing a usable preview.

## Beginner Quick Create

The desktop app opens in Beginner Mode. The fastest path is:

1. Select media, an image folder, or an asset folder.
2. Pick a premium template.
3. Type a plain-English request in **One-Click Quick Create**.
4. Click **Generate Preview**.

The app derives product name, goal, features, vibe, duration, platform defaults, caption sizing, export preset, and render cache behavior from the selected template plus prompt. It still writes a normal `project.json` behind the scenes, so Advanced Mode can inspect and edit the generated result.

## Smart Defaults

Smart defaults are chosen from template and platform:

- Vertical platforms use `1080x1920`, large captions, Shorts/TikTok presets, and louder short-form normalization.
- Landscape templates use `1920x1080`, smaller captions, YouTube presets, and calmer audio normalization.
- Square exports use `1080x1080` and conservative 30 FPS defaults.
- Aggressive templates get stronger transition intensity; cinematic templates use smoother, lower-intensity motion.

The generated JSON stores these choices in `metadata.beginnerAutoTemplate.smartDefaults`.

## Beginner vs Advanced Mode

Beginner Mode hides JSON, keyframes, render graph details, low-level render settings, and advanced panels. Advanced Mode remains one click away and exposes JSON editor, timeline, assets, preview review, AI tools, render queue, and product diagnostics.

## Fast Iteration

Beginner Mode includes quick actions for:

- alternate hook prompt
- music swap
- duplicate current edit in memory
- try next template

These actions are intentionally small and reversible, letting users test changes without restarting the full workflow.

## Local-Only Friction Logging

The desktop app records workflow friction events on-device in Electron user data:

- slow operations
- failed operations
- failed exports
- repeated settings changes
- fast iteration actions

The Product panel can refresh a friction report that summarizes recent events and repeated labels. No telemetry, accounts, network sync, or cloud logging are used.

## Implementation Notes

- `src/beginner/auto_template.py` owns backend smart-default metadata.
- `desktop-app/src/App.tsx` owns beginner quick create, mode separation, and fast iteration UI.
- `desktop-app/electron/main.ts` writes the local JSONL friction log.
- `desktop-app/electron/preload.ts` exposes the IPC bridge.

