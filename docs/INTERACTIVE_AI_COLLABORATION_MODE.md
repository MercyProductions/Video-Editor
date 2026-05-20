# Interactive AI Collaboration Mode

Interactive AI Collaboration Mode makes the processing dock usable while generation or rendering is happening. It does not replace the JSON engine; every approval, caption edit, pacing change, and assistant instruction mutates the current project JSON.

## Live Scene Generation

The AI Activity dock now shows draft scene cards from the active timeline:

- scene label and status
- editable caption text
- selected clip or media layer
- transition choice
- pacing classification
- confidence indicator
- readability/pacing warnings

Scene cards update from the same `project.json` timeline used by the renderer.

## Inline Controls

Each scene card supports:

- approve
- regenerate
- lock
- skip from final export
- faster pacing
- slower pacing
- partial scene preview
- caption edit on blur

These controls use the existing non-destructive preview review helpers in `desktop-app/src/lib/project.ts`.

## Live Suggestions

The dock suggests practical fixes from project heuristics:

- shorter hook when the intro is long
- caption readability when lines are too dense
- smoother transitions when one transition repeats heavily
- cinematic style when no strong style metadata exists
- review prompts when sections still need approval

Suggestions apply through the same assistant instruction path, so they remain inspectable in JSON.

## Assistant Sidebar

The sidebar accepts direct instructions such as:

- `make this darker`
- `slow down the captions`
- `zoom more on the dashboard`
- `make this feel more cinematic`
- `remove excessive motion`

The first implementation is deterministic and local-first. It applies safe metadata and timeline edits rather than depending on a remote model.

## Partial Preview

Scene cards can jump into scene-only preview using the existing interactive preview renderer. This lets users review generated sections without waiting for a full final export.

