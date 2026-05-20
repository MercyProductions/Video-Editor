# Export Packaging And Posting Prep

Posting packages turn a rendered MP4 into local upload-ready folders for common creator platforms. The command does not upload anything and does not require accounts or cloud services.

## Command

```powershell
python render.py post-package examples/generated/phase14_approved_preview/project.json examples/generated/phase14_approved_preview/final_video.mp4 --platforms all -o exports/phase15_posting_package
```

Supported platforms:

- `youtube_shorts`
- `youtube_landscape`
- `tiktok`
- `instagram_reels`
- `discord`
- `high_quality_archive`
- `x_twitter`

Aliases such as `shorts`, `youtube`, `youtube_1080p`, `instagram`, `reels`, `discord_720p`, `archive`, `x`, and `twitter` are accepted.

## Package Contents

Each platform folder contains:

- `final_video.mp4`
- `thumbnail.png`
- `thumbnail_options/option_1.png`
- `thumbnail_options/option_2.png`
- `thumbnail_options/option_3.png`
- `title.txt`
- `title_ideas.txt`
- `description.txt`
- `hashtags.txt`
- `pinned_comment.txt`
- `cta.txt`
- `upload_notes.txt`
- `captions.srt`
- `captions.vtt`
- `transcript.txt`
- `burned_in_captions.txt`
- `render_report.json`
- `quality_checklist.json`
- `package_manifest.json`

The root folder is now the default upload package and contains:

- `final_video.mp4`
- `thumbnail.png`
- `captions.srt`
- `captions.vtt`
- `transcript.txt`
- `title.txt`
- `description.txt`
- `hashtags.txt`
- `pinned_comment.txt`
- `cta.txt`
- `upload_notes.txt`
- `render_report.json`
- `project_backup.json`
- `assets_used.json`
- `metadata.json`
- `quality_checklist.json`
- `export_validation.json`
- `package_manifest.json`
- `version_history.json`
- `posting_package_summary.json`

The local archive folder contains:

- `local_archive/project_backup.json`
- `local_archive/final_video.mp4`
- `local_archive/assets_used.json`
- `local_archive/render_report.json`
- `local_archive/render_logs.txt`
- `local_archive/metadata.json`
- `local_archive/version_history.json`

## Quality Checklist

The package checks:

- video exists and can be inspected
- duration
- resolution
- audio stream
- audio loudness/clipping risk
- caption readability issues
- text safe-zone issues
- file size against platform package expectations

Warnings are written into each platform `quality_checklist.json`. A package can still be useful with warnings, but warnings should be reviewed before uploading.

## Desktop App

Final renders from the Render Panel automatically create a delivery package after the MP4 completes. The render queue shows progress, current scene, ETA, package status, and package path.

In the Product pane:

1. Render a preview or final MP4.
2. Choose target platforms.
3. Click `Create Upload Package`.
4. Open the generated folder from the status path.
