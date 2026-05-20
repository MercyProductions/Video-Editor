# Content Repurposing Mode

Content Repurposing Mode turns one finished edit into multiple platform-ready JSON projects without starting over. It keeps the original assets non-destructive and writes normal project JSON for every variant.

## Create Repurposed Project JSON

```powershell
python render.py repurpose examples/generated/phase14_approved_preview/project.json --platforms youtube_shorts tiktok instagram_reels youtube_landscape discord x_twitter --hook all --cta all --max-variants 24 -o output/repurposed_content
```

Supported platforms:

- `youtube_shorts`
- `tiktok`
- `instagram_reels`
- `youtube_landscape`
- `discord`
- `x_twitter`

Aliases such as `shorts`, `youtube`, `instagram`, `reels`, `twitter`, and `x` are accepted.

## Hook Variants

- `serious`
- `curiosity`
- `problem_solution`
- `fast_aggressive`
- `clean_professional`

Use `--hook all` to generate all hook variants.

## CTA Variants

- `subscribe`
- `visit_website`
- `download`
- `comment`
- `follow`

Use `--cta all` to generate all CTA variants.

## Batch Export

Add `--render --package` to render and create upload packages for each generated variant:

```powershell
python render.py repurpose examples/generated/phase14_approved_preview/project.json --platforms youtube_shorts --hook serious --cta subscribe --max-variants 3 --render --package --quality preview -o output/repurpose_batch
```

Each variant folder can contain:

- `project.json`
- `final_video.mp4`
- `render_report.json`
- `thumbnails/`
- `upload_package/`

## Style Reuse

By default, repurposed edits preserve successful style metadata:

- lighting
- pacing
- caption styling
- transitions
- brand kit metadata

Use `--no-reuse-style` only when you want neutral variants.

## Desktop App

In the Product tab, use **Content Repurposing**:

1. Choose target platforms.
2. Set max variants.
3. Keep style reuse enabled for successful edits.
4. Click `Generate JSONs` for fast editable variants.
5. Click `Batch Export` for rendered and packaged variants.
