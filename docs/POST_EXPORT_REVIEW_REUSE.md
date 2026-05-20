# Post-Export Review And Reuse

Post-export review runs after a final MP4 and delivery package exist. It stays local-only and helps decide whether to reuse, re-export, or create variants from a successful edit.

## Review A Finished Export

```powershell
python render.py post-export review examples/generated/phase14_approved_preview/project.json examples/generated/phase14_approved_preview/final_video.mp4 --package-dir output/final_delivery_package_smoke -o output/post_export_review.json
```

The review checks:

- playable video and decode errors
- audio presence and duration sync risk
- expected export resolution
- project duration vs rendered duration
- caption readability and caption package files
- thumbnail package file
- file size and compression risk

## Quick Re-Export JSON

```powershell
python render.py post-export reexport examples/generated/phase14_approved_preview/project.json --mode lower_size --preset low_size_preview --captions keep -o output/post_export_reexport
```

This writes a new editable `project.json` variant with updated export settings. Use normal rendering afterward:

```powershell
python render.py render output/post_export_reexport/project.lower_size.low_size_preview.json --quality final --preset low_size_preview -o output/reexport_low_size.mp4
```

Useful modes:

- `lower_size`
- `higher_quality`
- `platform`
- `captions_off`

## Save A Reusable Template

```powershell
python render.py post-export template examples/generated/phase14_approved_preview/project.json --video examples/generated/phase14_approved_preview/final_video.mp4 --name "Verified Reuse Template" -o output/verified_reuse_template.json
```

The saved template captures style, pacing, caption format, export settings, intro/outro structure, lighting profile, and transition usage.

## Create Variants

```powershell
python render.py post-export variants examples/generated/phase14_approved_preview/project.json --variant shorter --variant hook --variant cta --variant caption_style -o output/post_export_variants
```

Variant projects are normal JSON projects and can be rendered or edited like any other project.

## Save Success Notes

```powershell
python render.py post-export note examples/generated/phase14_approved_preview/project.json --video examples/generated/phase14_approved_preview/final_video.mp4 --profile "Aegis Creator" --tag good_pacing --tag reuse_this --note "Use this pacing and caption balance again."
```

Supported local tags:

- `good_pacing`
- `good_style`
- `reuse_this`
- `too_much_motion`
- `captions_too_fast`

## Desktop App

In the Product tab, use **Post-Export Review + Reuse** after final export. The panel can play the exported file, show thumbnail/caption/package checks, create quick re-export JSON, save a reusable template, generate variants, and save local success notes.
