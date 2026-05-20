# Preview Review And Edit Control

Preview Review turns the Preview tab into the approval surface before final export. The project JSON remains the source of truth: review markers, notes, scene status, A/B versions, and pause-time edits are saved into `metadata.previewReview` and scene metadata.

## Review Markers

While watching the cached interactive preview, a user can add timestamped markers:

- needs cut
- too slow
- too fast
- bad caption
- bad zoom
- bad transition
- audio issue
- keep this section

Markers are attached to the current scene and timestamp. Approving or locking a scene resolves its open markers.

## Pause And Edit

When paused on a scene, the Preview tab can edit:

- caption text
- scene start and duration
- transition type and duration
- zoom amount
- lighting intensity
- media asset
- scene lock
- scene removal

`Apply JSON` updates the project only. `Apply + Preview` updates the project and immediately rebuilds the interactive preview cache.

## Regeneration

Regeneration is deterministic and local. It updates JSON metadata and renderable scene instructions, then rebuilds the preview:

- current scene
- captions from this point
- transitions only
- music sync
- pacing
- selected range

Locked scenes are preserved.

## A/B Versions

Version A and Version B are local snapshots stored under `metadata.previewReview.versions`. Users can save either slot, compare duration/caption/style summaries, and restore a winner.

## Final Export Gate

When preview review is active, final export is blocked until:

- all non-excluded scenes are approved or locked
- unresolved review markers are resolved

The gate also shows duration, export format, platform preset, and quality-check status so the creator can catch problems before spending time on a final render.
