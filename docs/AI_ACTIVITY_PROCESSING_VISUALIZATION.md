# AI Activity and Processing Visualization

The desktop app now shows a global processing dock inside the workspace whenever the engine is working or recent activity exists. It is intentionally local and event-driven: it reflects app actions, streamed render logs, render queue state, generated review data, and preview/cache outputs.

## What It Shows

- current stage and active task
- progress percentage and ETA when available
- current asset or output path
- current render scene
- encoder/cache status
- active workers
- live activity feed
- generated timeline blocks
- optional AI reasoning summary

## Render Awareness

Electron already tracks FFmpeg render progress from engine log lines. The processing dock uses those events to show:

- scene render progress
- transition pass
- audio mix
- final encoding
- delivery package status
- render worker state

This avoids inventing fake progress while still keeping the app visibly alive.

## User Controls

The dock exposes queue controls without forcing the user into the Render panel:

- pause queue
- resume queue
- prioritize active job
- cancel active job
- jump to Preview
- continue in background

Non-render AI or editor actions cannot be interrupted yet unless their underlying engine command supports cancellation. The UI still shows the active stage, worker plan, heartbeat animation, and final activity result.

## Design Notes

The dock uses subtle motion only where it communicates liveness:

- animated progress indicator
- waveform movement
- AI pulse
- active scene pulse
- worker progress chips

The goal is confidence and clarity, not decoration.

