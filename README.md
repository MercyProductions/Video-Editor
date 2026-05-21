# Automatic Video Editor

Automatic Video Editor is a Python CLI engine and Electron desktop app that renders finished MP4 videos from JSON. The JSON project file remains the source of truth while the desktop UI provides editing, preview, assets, AI helpers, and render controls on top of the FFmpeg backend.

## Product Focus

The project is now in quality-first execution mode: stable over flashy, fast over overengineered, reliable over experimental, and cohesive over bloated. Future work should improve real workflows before adding new surface area.

Every future feature must justify creator value, performance cost, memory cost, UI complexity, render complexity, maintenance burden, and long-term scalability. See [docs/PRODUCT_ENGINEERING_CHARTER.md](docs/PRODUCT_ENGINEERING_CHARTER.md).

## Quick Start

```powershell
cd C:\Users\gabri\Desktop\Aegis\Tools\Kioson\automatic-video-editor
python -m pip install -r requirements.txt
python examples/create_sample_assets.py
python render.py render examples/project.json
```

The compatibility shortcut still works:

```powershell
python render.py examples/project.json
```

Rendered videos go to `output/final_video.mp4` unless `-o` is provided.

## Current Reliable Workflow

The currently verified path is the local MVP loop: create or open JSON, validate it, run quality checks, render a preview MP4, and use the desktop app as a UI over that same JSON source of truth.

```powershell
python render.py validate examples/project.json
python render.py quality-check examples/project.json -o output/quality_report.json
python render.py render examples/project.json -o output/smoke_preview.mp4 --quality preview --cache
```

For a generated starter project:

```powershell
python render.py quick-create examples/assets/gameplay.mp4 --music examples/assets/song.wav --logo examples/assets/logo.png --title "Automatic Edit" --caption "JSON to FFmpeg to MP4." --duration 4 -o examples/generated/quick_create.json --render --render-output output/quick_create_preview.mp4 --quality preview --cache
```

Current feature status:

- Stable: JSON validation, asset resolution, clear missing-asset errors, sample preview render, quick-create JSON generation/render, render reports, quality checks, desktop typecheck/build.
- Smoke-tested: demo JSON validation, Electron production build, preview render caching, beginner quick-create backend path.
- Experimental: broad local AI/content workflows, advanced cinematic systems, adaptive memory, proactive suggestions, plugin expansion, packaged installer flow.
- Planned hardening: desktop unit tests, isolated packaging tests, larger render matrix, duration assertions, file/module split of the large UI and CLI entry points.

Run the local gate before trusting a handoff build:

```powershell
python scripts/verify_local.py
```

## Desktop App

Phase 4 adds an Electron, React, and TypeScript desktop shell in `desktop-app/`. It uses the existing Python renderer through IPC, so every UI action still reads or writes the same `project.json` format used by the CLI.

```powershell
cd C:\Users\gabri\Desktop\Aegis\Tools\Kioson\automatic-video-editor\desktop-app
npm install
npm run dev
```

Production build check:

```powershell
npm run typecheck
npm run build
npm run dist
```

Desktop panels:

- Beginner Mode: New Auto Video flow with file pickers, premium template picker, simple product form, preview render, final render, and hidden `project.json` generation.
- Main dashboard: new project, open project, recent projects, template gallery, render queue.
- JSON editor: Monaco editing, schema diagnostics, autocomplete from `src/schema/project.schema.json`, validate, and AI repair.
- Visual timeline: scene blocks, layer tracks, audio track, transitions, draggable scene duration handles, timeline zoom.
- Preview window: interactive preview cache, play/pause/stop/restart, scrubbing, scene jumping, frame stepping, speed, volume, loop, thumbnails, waveform, and safe-zone overlays.
- Asset library: import media into the project asset folder, thumbnail previews, missing asset detection, drag/double-click insertion into scenes.
- AI panel: autonomous production pipeline, prompt-to-video JSON, explain project, repair JSON, suggest transitions, generate captions, and create scenes.
- Render panel: preview/final render, export preset selector, cache/resume/GPU options, progress logs, and open output folder.
- AI Activity dock: global processing view with stage, progress, ETA, current scene/asset, worker status, activity feed, timeline generation preview, and queue controls. See [docs/AI_ACTIVITY_PROCESSING_VISUALIZATION.md](docs/AI_ACTIVITY_PROCESSING_VISUALIZATION.md).
- Interactive AI Collaboration: live scene cards, inline approval/regeneration/locking, caption edits, confidence indicators, suggestions, assistant instructions, and partial scene preview while work is in progress. See [docs/INTERACTIVE_AI_COLLABORATION_MODE.md](docs/INTERACTIVE_AI_COLLABORATION_MODE.md).
- Adaptive Workflow Intelligence: local-only workflow memory that learns preferred templates, pacing, caption density, motion intensity, export presets, hook style, recovery corrections, and session continuity. See [docs/ADAPTIVE_WORKFLOW_INTELLIGENCE.md](docs/ADAPTIVE_WORKFLOW_INTELLIGENCE.md).
- Proactive Creative Assistance: right-rail production coach with predictive issue detection, creative opportunities, optimization suggestions, and idle background improvement candidates. See [docs/PROACTIVE_CREATIVE_ASSISTANCE.md](docs/PROACTIVE_CREATIVE_ASSISTANCE.md).
- Phase 5 workflow panes: AI Director, storyboard, asset intelligence, version history, render queue controls, project packaging, and plugin management.
- Phase 6 product pane: real-time cached frame preview, quality checks, collaboration manifests, social reformatting, brand kits, offline template packs, recovery points, settings, themes, and keyboard shortcuts.

Packaged app output is prepared under `desktop-app/release/win-unpacked`. Installer-ready scripts are available through `npm run dist` for an unpacked app and `npm run build:installer` for Windows installer artifacts.

## Phase 6 Product Polish

Phase 6 focuses on reliability, portability, and production workflow rather than adding another layer of random features.

Real-time preview renders a cached representative frame without exporting the full video:

```powershell
python render.py realtime-preview examples/project.json --time 1 -o output/realtime_preview
```

Quality checks catch missing/low-resolution assets, text outside safe zones, poor contrast, caption pacing, missing audio, clipping risks, and export setting problems:

```powershell
python render.py quality-check examples/project.json -o output/quality_report.json
```

Collaboration manifests hash assets and report portability/version compatibility:

```powershell
python render.py manifest examples/project.json -o output/project_manifest.json
python render.py manifest examples/project.json --check-only
```

Brand kits can define logo, colors, fonts, intro/outro, watermark, default caption style, and default transitions:

```powershell
python render.py brand init -o examples/generated/brand_kit.json
python render.py brand apply examples/project.json examples/generated/brand_kit.json -o examples/generated/branded_project.json
```

Social reformatting emits platform variants from one source project:

```powershell
python render.py reformat examples/project.json --targets youtube tiktok instagram_square shorts discord -o examples/generated/social_reformats
```

Offline template packs are portable local zips with metadata, author, tags, preview thumbnail path, required assets, and template JSON:

```powershell
python render.py pack export examples/templates/gaming_montage.json --type template -o output/gaming_template_pack.templatepack
python render.py pack import output/gaming_template_pack.templatepack
python render.py pack list
```

Crash recovery provides autosaves, backups, recovery listing, and restore:

```powershell
python render.py recovery autosave examples/project.json
python render.py recovery backup examples/project.json
python render.py recovery list examples/project.json
python render.py recovery restore examples/.ave_recovery/autosaves/project.some-id.json examples/generated/recovered_project.json
```

## Phase 7 Automated Content Workflows

Phase 7 adds a vertical local-first workflow that can go from an idea plus assets to a rendered edit. It reuses the existing JSON renderer, clip selector, beat sync, storyboard, thumbnail, and render cache instead of creating a parallel pipeline.

Run a full autonomous idea-to-review pipeline with a preview render and explainability packet:

```powershell
python render.py autonomous "Create a 35 second premium red black showcase for my automatic troubleshooter. It scans missing runtimes, launch blockers, anti-cheat conflicts, and Windows security settings." --assets examples/assets --music examples/assets/beat_music.wav --logo examples/assets/logo.png --platform shorts --content-type product_showcase --vibe "premium red black cinematic" --render-preview --cache -o examples/generated/autonomous_troubleshooter
```

Autonomous mode writes `autonomous_plan.json`, `content_plan.json`, `generation_review.json`, `project.json`, `preview_video.mp4`, `autonomous_quality_review.json`, `autonomous_variants.json`, and an explainability report. Final render and posting packages are gated by `--approved`. See [docs/AUTONOMOUS_PRODUCTION_PIPELINE.md](docs/AUTONOMOUS_PRODUCTION_PIPELINE.md).

Generate a complete short-form video plan in one of five content modes:

```powershell
python render.py content-generate "Create a YouTube Short for Automatic Troubleshooter with runtime scans, launch blocker detection, anti-cheat checks, and Windows security fixes" --mode youtube_shorts --product-name "Automatic Troubleshooter" --assets examples/assets --music examples/assets/beat_music.wav --logo examples/assets/logo.png --duration 15 --tone cinematic -o examples/generated/content_generator_rendered --render --quality preview --cache
```

Modes: `youtube_shorts`, `tiktok`, `product_showcase`, `tutorial`, and `promo_ad`. The generator writes `content_brief.json`, `script.json`, `scene_plan.json`, `content_plan.json`, `generation_review.json`, `approval_state.json`, `ai_reasoning_summary.txt`, `review_summary.txt`, `project.json`, preview reports, and `final_video.mp4` when preview rendering is used. See [docs/CONTENT_GENERATOR_MODE.md](docs/CONTENT_GENERATOR_MODE.md).

Review, approve, regenerate, and compare generated sections before final export:

```powershell
python render.py content-review show examples/generated/content_generator_rendered/content_plan.json
python render.py content-review approve examples/generated/content_generator_rendered/content_plan.json --section all --status approved
python render.py content-generate "Make the captions cleaner" --mode youtube_shorts --existing-plan examples/generated/content_generator_rendered/content_plan.json --regenerate captions --lock scene:problem -o examples/generated/content_generator_captions_v2
python render.py content-review compare examples/generated/content_generator_rendered/content_plan.json examples/generated/content_generator_captions_v2/content_plan.json -o examples/generated/content_generator_compare
```

Final-quality renders from generated content are gated by approval. Preview renders remain available for review. See [docs/CONTENT_REVIEW_WORKFLOW.md](docs/CONTENT_REVIEW_WORKFLOW.md).

Create local upload-ready posting packages after a render:

```powershell
python render.py post-package examples/generated/phase14_approved_preview/project.json examples/generated/phase14_approved_preview/final_video.mp4 --platforms all -o exports/phase15_posting_package
```

This creates a root upload package plus platform folders for YouTube Shorts, TikTok, Instagram Reels, YouTube landscape, Discord, high-quality archive, and X/Twitter. The package includes the MP4, thumbnail, title/description/hashtags, pinned comment, CTA, upload notes, `.srt`, `.vtt`, transcript, render report, project backup, archive files, and export validation. See [docs/POSTING_PACKAGE.md](docs/POSTING_PACKAGE.md).

Review a finished export and reuse successful settings:

```powershell
python render.py post-export review examples/generated/phase14_approved_preview/project.json examples/generated/phase14_approved_preview/final_video.mp4 --package-dir exports/phase15_posting_package -o output/post_export_review.json
python render.py post-export reexport examples/generated/phase14_approved_preview/project.json --mode lower_size --preset low_size_preview -o output/post_export_reexport
python render.py post-export variants examples/generated/phase14_approved_preview/project.json --variant shorter --variant hook --variant caption_style -o output/post_export_variants
python render.py post-export note examples/generated/phase14_approved_preview/project.json --tag good_pacing --tag reuse_this --note "Reuse this pacing."
```

This adds playback/export diagnostics, quick re-export JSON, reusable template capture, editable variants, and local success notes. See [docs/POST_EXPORT_REVIEW_REUSE.md](docs/POST_EXPORT_REVIEW_REUSE.md).

Repurpose one strong edit into platform-ready variants:

```powershell
python render.py repurpose examples/generated/phase14_approved_preview/project.json --platforms youtube_shorts tiktok instagram_reels youtube_landscape discord x_twitter --hook all --cta all --max-variants 24 -o output/repurposed_content
python render.py repurpose examples/generated/phase14_approved_preview/project.json --platforms youtube_shorts --hook serious --cta subscribe --max-variants 3 --render --package --quality preview -o output/repurpose_batch
```

Repurposing creates normal project JSON variants with platform aspect ratios, caption/safe-zone adjustments, hook and CTA alternatives, preserved style metadata, optional renders, thumbnails, and upload packages. See [docs/CONTENT_REPURPOSING.md](docs/CONTENT_REPURPOSING.md).

Repeatable creator workflow automation:

```powershell
python render.py workflow profile "Aegis Creator" -o profiles/aegis_creator.creator-profile.json
python render.py workflow pipeline-create "Cybersecurity Tool Demo" --preset cybersecurity_tool_demo --profile profiles/aegis_creator.creator-profile.json -o workflows/pipelines/cybersecurity_tool_demo.workflow.json
python render.py workflow batch workflows/pipelines/cybersecurity_tool_demo.workflow.json "Create shorts for Automatic Troubleshooter showing runtime scans, launch blockers, anti-cheat checks, and Windows security settings" --assets examples/assets --music examples/assets/beat_music.wav --logo examples/assets/logo.png --versions 2 -o examples/generated/phase16_workflow_batch
python render.py workflow dashboard --project examples/generated/phase16_workflow_batch/v01_serious_cinematic/project.json -o output/phase16_dashboard.json
```

Phase 16 adds reusable profiles, saved content pipelines, batch variants, local scheduled tasks, creator memory, asset reuse intelligence, and a production dashboard. See [docs/CREATOR_WORKFLOW_AUTOMATION.md](docs/CREATOR_WORKFLOW_AUTOMATION.md).

Local quality feedback loops:

```powershell
python render.py feedback analyze examples/generated/phase16_workflow_rendered/v01_serious_cinematic/project.json --video examples/generated/phase16_workflow_rendered/v01_serious_cinematic/final_video.mp4 -o output/phase17_self_analysis.json
python render.py feedback review examples/generated/phase16_workflow_rendered/v01_serious_cinematic/project.json --video examples/generated/phase16_workflow_rendered/v01_serious_cinematic/final_video.mp4 --plan examples/generated/phase16_workflow_rendered/v01_serious_cinematic/content_plan.json --profile "Aegis Creator" --pacing 4 --readability 4 --transitions 3 --cinematic 5 --hook 5 --captions 4 --polish 4
python render.py feedback learn "Aegis Creator" -o output/phase17_creator_identity.json
python render.py feedback dataset "Aegis Creator" -o output/phase17_training_dataset --min-rating 4
```

Phase 17 adds post-render ratings, self-analysis, style consistency scoring, hook effectiveness analysis, AI improvement signals, creator identity learning, and local-only dataset export. See [docs/QUALITY_FEEDBACK_LOOPS.md](docs/QUALITY_FEEDBACK_LOOPS.md).

Long-term evolution quality gate:

```powershell
python render.py evolution-report --project examples/generated/phase17_identity_workflow_batch/v01_serious_cinematic/project.json --profile "Aegis Creator" -o output/long_term_evolution_report.json
```

This aggregates architecture, workflow health, project intelligence, creator identity, local AI status, performance, and controlled-expansion guidance so future work stays cohesive instead of bloated. See [docs/LONG_TERM_EVOLUTION.md](docs/LONG_TERM_EVOLUTION.md).

Beginner Auto-Template Mode for non-technical creation:

```powershell
python render.py auto-template list
python render.py auto-template create --media examples/assets/gameplay.mp4 --music examples/assets/beat_music.wav --logo examples/assets/logo.png --template premium_product_showcase --product-name "Automatic Troubleshooter" --goal "Show how it scans launch blockers and fixes setup problems" --feature "Missing runtimes" --feature "Anti-cheat conflicts" --feature "Windows security settings" --vibe "premium red black cinematic" --duration 12 -o examples/generated/beginner_auto_template --render --quality preview --cache
```

The desktop app exposes the same workflow through **New Auto Video**. It generates `project.json` internally and keeps Advanced Mode available for JSON/timeline edits. See [docs/BEGINNER_AUTO_TEMPLATE_MODE.md](docs/BEGINNER_AUTO_TEMPLATE_MODE.md).

Workflow friction reduction builds on Beginner Mode with a one-click quick-create prompt, automatic smart defaults for platform/template, beginner-vs-advanced separation, fast iteration controls, and local-only friction logging:

```powershell
cd C:\Users\gabri\Desktop\Aegis\Tools\Kioson\automatic-video-editor\desktop-app
npm run dev
```

Open **New Auto Video**, select media, choose a template, type a short request, and generate a preview. See [docs/WORKFLOW_FRICTION_REDUCTION.md](docs/WORKFLOW_FRICTION_REDUCTION.md).

Adaptive workflow memory now personalizes those defaults over time. The desktop app writes a local `adaptive-workflow-memory.json` file inside Electron user data, uses it to suggest showcase/montage/tutorial/caption-heavy modes from imported media, adapts to repeated corrections, and shows the creator fingerprint in the Product pane. See [docs/ADAPTIVE_WORKFLOW_INTELLIGENCE.md](docs/ADAPTIVE_WORKFLOW_INTELLIGENCE.md).

Professional media compatibility:

```powershell
python render.py media formats
python render.py media inspect examples/assets/gameplay.mp4 -o output/media_inspect_gameplay.json
python render.py media import output/media_compat_inputs/gameplay_test.mov output/media_compat_inputs/beat_test.ogg --project-dir examples/generated/media_compat_import
python render.py render examples/project.json -o output/compat_export.webm
python render.py render examples/project.json -o output/compat_export.gif
```

Supported import formats now include common video containers such as MP4, MOV, MKV, AVI, WebM, FLV, WMV, MPEG/MPG, M4V, TS/MTS/M2TS; image formats such as PNG, JPG, WebP, BMP, GIF, TIFF, and SVG; and audio formats such as MP3, WAV, FLAC, OGG, AAC, and M4A. The smart import pipeline writes metadata, thumbnails, waveforms, proxies, and normalized media when needed. Export supports MP4, MOV, MKV, WebM, GIF, and image sequences. See [docs/MEDIA_COMPATIBILITY.md](docs/MEDIA_COMPATIBILITY.md).

Create a structured YouTube Short from a prompt:

```powershell
python render.py youtube-short "Create a YouTube Short for my automatic troubleshooter. It scans missing runtimes, launch blockers, anti-cheat conflicts, and Windows security settings. Make it premium red/black, cinematic, and under 45 seconds." --assets examples/assets --music examples/assets/beat_music.wav --logo examples/assets/logo.png -o examples/generated/youtube_short_auto --render --quality preview --cache
```

This writes `project.json`, `short_plan.json`, `review_summary.txt`, preview reports, and `final_video.mp4` when `--render` is used. See [docs/YOUTUBE_SHORTS_MODE.md](docs/YOUTUBE_SHORTS_MODE.md).

Run a complete pipeline:

```powershell
python render.py pipeline "Create a 12 second premium red black showcase for an automatic troubleshooter with runtime scans and launch blocker fixes" examples/assets --music examples/assets/beat_music.wav --style red_black_aegis --preset shorts --duration 12 -o examples/generated/phase7_pipeline --render --quality preview
```

The pipeline writes:

- `project.json`
- `clip_selection.json`
- `music_analysis.json` when music is supplied
- `preview/timeline_summary.json`
- `preview/render_plan.txt`
- `storyboard/storyboard.json`
- `thumbnails/thumbnail_report.json` when rendering is enabled
- `pipeline_summary.json`
- `final_video.mp4` when `--render` is used

Batch A/B generation:

```powershell
python render.py batch "Create a quick product showcase from these clips" examples/assets --music examples/assets/beat_music.wav --styles clean_cinematic red_black_aegis --presets shorts square --versions 2 -o examples/generated/batch_tests
```

Highlight detection now reports motion spikes, loud reaction candidates, possible impact/payoff moments, silence/dead sections, and a ranked highlight score:

```powershell
python render.py highlight-detect examples/assets --scene-duration 2 --max-clips 3 -o output/highlights.json
```

Smart captions add punctuation-aware timing and emphasis metadata:

```powershell
python render.py captions examples/project.json examples/transcript.srt --mode smart --style tiktok -o examples/generated/smart_captions.json
```

Thumbnail variations:

```powershell
python render.py thumbnail output/final_video.mp4 --title "Runtime Fixes" -o output/thumbnails
```

Scene suggestions, creator profiles, local automation hooks, and metrics:

```powershell
python render.py suggest examples/generated/phase7_pipeline/project.json
python render.py profile create MyCreator
python render.py automation queue examples/generated/phase7_pipeline -o output/queue
python render.py metrics summary -o output/metrics_summary.json
```

## Phase 8 Cinematic Intelligence

Phase 8 adds renderable cinematic primitives on top of the existing JSON engine: camera simulation, motion graphics layers, effect graph post-processing, clip/audio understanding, smart scene building, and project analysis.

Build and render a self-contained hype intro:

```powershell
python render.py scene-build "build hype intro for automatic troubleshooter" --duration 6 --preset shorts --style red_black_aegis -o examples/generated/phase8_hype_intro.json --render --quality preview
```

Apply cinematic camera movement, progress graphics, HUD overlays, effect graph grading, and mix-safe audio settings to an existing project:

```powershell
python render.py cinematic-enhance examples/project.json --preset premium_red_black -o examples/generated/phase8_cinematic_project.json
python render.py render examples/generated/phase8_cinematic_project.json -o output/phase8_cinematic_preview.mp4 --quality preview --cache
```

Analyze footage and music locally:

```powershell
python render.py understand-clip examples/assets/gameplay.mp4 -o output/phase8_clip_understanding.json
python render.py audio-intel examples/assets/beat_music.wav -o output/phase8_audio_intel.json
```

Analyze the finished edit for pacing, caption density, transition repetition, effects, loudness, and boring sections:

```powershell
python render.py project-analyze examples/generated/phase8_cinematic_project.json --rendered-video output/phase8_cinematic_preview.mp4 -o output/phase8_project_analysis.json
```

Effect graph presets:

```powershell
python render.py effect-graph list
```

## Phase 9 Local-First Creator Platform

Phase 9 adds local ecosystem foundations around the renderer: workspace state, review notes, SQLite asset indexing, offline packs, same-machine render workers, local AI helpers, anonymized dataset export, creator analytics, API/engine descriptors, local-first policy, and diagnostics. It does not add cloud sync, cloud rendering, remote backup, online collaboration, telemetry, accounts, or marketplace servers.

Workspace and review state:

```powershell
python render.py workspace init Phase9 -o output/phase9_workspace.json
python render.py workspace open output/phase9_workspace.json examples/project.json
python render.py workspace layout output/phase9_workspace.json --preset advanced
python render.py review comment examples/project.json intro "Tighten the logo reveal" --time 1.2
python render.py review marker examples/project.json main_clip keep --time 4.5 --note "Strong showcase moment"
python render.py review approve examples/project.json intro approved
python render.py review report examples/project.json -o output/phase9_review_report.json
```

Asset database:

```powershell
python render.py asset-db index examples/assets
python render.py asset-db usage examples/project.json
python render.py asset-db search gameplay --limit 5
python render.py asset-db duplicates
python render.py asset-db report -o output/phase9_asset_db_report.json
```

Offline packs and local dataset export:

```powershell
python render.py pack export examples/templates/gaming_montage.json --type template --name phase9_gaming_pack -o output/phase9_gaming.templatepack
python render.py pack import output/phase9_gaming.templatepack
python render.py pack list
python render.py dataset-export examples/project.json examples/generated/phase8_cinematic_project.json -o output/phase9_training_dataset.json
```

Local render workers and local AI helpers:

```powershell
python render.py worker enqueue examples/project.json -o output/phase9_worker_render.mp4
python render.py worker run
python render.py worker status
python render.py local-ai status
python render.py local-ai prompt-json "Create a short red black product intro" -o examples/generated/local_ai_project.json
python render.py local-ai suggest examples/project.json -o output/local_ai_suggestions.json
```

Analytics, API surface, local-first policy, and diagnostics:

```powershell
python render.py analytics summary -o output/phase9_creator_analytics.json
python render.py api describe
python render.py api engines
python render.py local-policy init -o output/phase9_local_policy.json
python render.py diagnostics run examples/project.json -o output/phase9_diagnostics.json
```

The local policy explicitly records that network-dependent features are disabled. Render workers run on the same machine only.

## Phase 5 Workstation

AI Director rewrites an existing project toward a goal while preserving approved scenes, saving history, analyzing assets, improving pacing, adding captions, resolving B-roll requests, and applying music timing when possible.

```powershell
python render.py director examples/project.json "Make this feel like a fast gaming montage" -o examples/generated/director_gaming_project.json
python render.py history list examples/project.json
python render.py history rollback examples/project.json 20260519T225044Z_9143c930 -o examples/generated/rollback_preview.json
```

Storyboard generation creates thumbnails, timing maps, transition maps, and scene summaries before render:

```powershell
python render.py storyboard examples/project.json -o output/storyboard
```

Asset intelligence detects duration, resolution, FPS, audio presence, loudness, motion, dominant colors, file size, codec, and issues:

```powershell
python render.py asset-analyze examples/project.json -o output/asset_intelligence.json
```

B-roll placeholders can be written directly in JSON:

```json
{
  "type": "broll",
  "query": "gameplay action",
  "layout": "center"
}
```

Resolve them before render, or let the parser resolve them during normal loading:

```powershell
python render.py resolve-broll examples/broll_project.json -o examples/generated/broll_resolved_project.json
python render.py render examples/generated/broll_resolved_project.json -o output/broll_smoke.mp4 --quality preview --cache
```

Project packaging exports a portable zip with JSON, bundled assets, reports, and template metadata. Opening the package extracts a project that points at its bundled assets.

```powershell
python render.py package export examples/project.json -o output/project_package.zip
python render.py package open output/project_package.zip -o output/opened_package
```

Plugins are manifest-based scaffolds for custom transitions, effects, templates, and export presets:

```powershell
python render.py plugin list
python render.py plugin init punch_zoom transition
```

## CLI Commands

```powershell
python render.py render examples/project.json
python render.py validate examples/project.json
python render.py preview examples/project.json
python render.py repair examples/bad_project.json
python render.py template list
python render.py template create gaming_montage
python render.py ai-generate "Create a 20 second gaming montage with fast cuts, red black theme, captions, and bass drop transitions."
python render.py preset list
python render.py analyze-audio examples/assets/beat_music.wav
python render.py beat-sync examples/project.json --audio examples/assets/beat_music.wav
python render.py auto-select examples/assets
python render.py smart-build examples/assets --music examples/assets/beat_music.wav
python render.py captions examples/project.json examples/transcript.srt --mode word
python render.py style list
python render.py director examples/project.json "Make this feel like a fast gaming montage"
python render.py storyboard examples/project.json
python render.py asset-analyze examples/project.json
python render.py resolve-broll examples/broll_project.json
python render.py package export examples/project.json
python render.py plugin list
python render.py realtime-preview examples/project.json --time 1
python render.py quality-check examples/project.json
python render.py manifest examples/project.json
python render.py brand init
python render.py brand apply examples/project.json examples/generated/brand_kit.json
python render.py reformat examples/project.json --targets youtube tiktok instagram_square shorts discord
python render.py pack list
python render.py pack export examples/templates/gaming_montage.json --type template
python render.py recovery autosave examples/project.json
python render.py autonomous "Create a premium red black showcase for my automatic troubleshooter" --assets examples/assets --music examples/assets/beat_music.wav --render-preview
python render.py pipeline "Create a fast product showcase" examples/assets --music examples/assets/beat_music.wav --render
python render.py batch "Create A/B short-form edits" examples/assets --styles clean_cinematic red_black_aegis --presets shorts square
python render.py highlight-detect examples/assets
python render.py thumbnail output/final_video.mp4 --title "Auto Showcase"
python render.py suggest examples/project.json
python render.py profile create MyCreator
python render.py automation queue examples/generated/phase7_pipeline
python render.py metrics summary
python render.py cinematic-enhance examples/project.json --preset premium_red_black
python render.py scene-build "build hype intro for automatic troubleshooter" --render
python render.py understand-clip examples/assets/gameplay.mp4
python render.py audio-intel examples/assets/beat_music.wav
python render.py project-analyze examples/project.json
python render.py effect-graph list
python render.py workspace init MyWorkspace
python render.py review report examples/project.json
python render.py asset-db index examples/assets
python render.py pack list
python render.py dataset-export examples/project.json
python render.py analytics summary
python render.py api describe
python render.py local-policy show
python render.py diagnostics run examples/project.json
python render.py worker status
python render.py local-ai status
```

Useful render flags:

```powershell
python render.py render examples/project.json -o output/custom.mp4
python render.py render examples/project.json --preset discord
python render.py render examples/project.json --preview
python render.py render examples/project.json --repair
python render.py render examples/project.json --generate-placeholders
python render.py render examples/project.json --keep-temp --log-level DEBUG
python render.py render examples/project.json --quality preview --cache
python render.py render examples/project.json --resume --cache
python render.py render examples/project.json --gpu
python render.py render examples/project.json --backend hybrid
```

## JSON Format

Top-level fields:

- `metadata`: optional notes, template metadata, AI prompt, required assets.
- `exportPreset`: optional preset key such as `youtube_1080p` or `tiktok_reels`.
- `project`: width, height, fps, duration, background, optional `crf`.
- `assets`: named file or folder references.
- `timeline`: ordered scenes with layers and transitions.
- `audio`: music and SFX tracks.
- `captions`: optional global caption data for future workflows.

Layer types:

- `video`: asset, position, trim, speed, crop, scale, blur, brightness, contrast, opacity.
- `image`: asset, position, scale, opacity, animations.
- `text`: text, font size, font family, color, stroke, shadow, box styling.
- `caption` / `captions`: timed caption items.
- `shape`, `progress`, `lower_third`, `hud`, `animated_background`, `particle`, `waveform`: FFmpeg-rendered motion graphics for title cards, HUDs, progress bars, animated backgrounds, and waveform-style visualizers.

Positions support pixels, percentages, and keywords: `center`, `middle`, `left`, `right`, `top`, `bottom`.

## Supported Effects

Animations:

- `fade`
- `slideUp`, `slideDown`, `slideLeft`, `slideRight`
- `zoomIn`, `zoomOut`
- `shake`
- `pulse`
- `typewriter`

Transitions:

- `cut`
- `crossfade`
- `fadeToBlack`
- `slide`
- `zoom`

Audio supports volume, start time, duration, trim, loop, fade in, and fade out.

Phase 8 audio tracks can also opt into render-time mix filters:

- `compressor`
- `limiter`
- `normalize`
- `ducking`
- `noiseReduction`
- `voiceIsolation`
- `bassEmphasis`

Scene-level post-processing can use `effectGraphPreset`, `effectGraph.nodes`, or `postProcessing` with color grading, vignette, glow, blur, sharpen, tint, and LUT nodes.

## Phase 3 Intelligence

### Beat Sync

Analyze music for beats, bass drops, BPM, loudness peaks, and quiet sections:

```powershell
python render.py analyze-audio examples/assets/beat_music.wav -o output/beat_music_analysis.json
```

Apply that timing to a project. The engine retimes scenes, places transitions near beat hits, adds zoom transitions near bass drops, and adds shake/pulse hits to text/media layers:

```powershell
python render.py beat-sync examples/project.json --audio examples/assets/beat_music.wav -o examples/generated/beat_synced_project.json
python render.py render examples/generated/beat_synced_project.json -o output/beat_synced_example.mp4 --quality preview --cache
```

### Auto Clip Selector

Scan a folder of clips, estimate duration, motion intensity, audio loudness, highlight windows, and dead footage:

```powershell
python render.py auto-select examples/assets --scene-duration 2 --max-clips 3 -o output/clip_selection.json
```

The selector samples video frames with FFmpeg and ranks clips by motion and loudness. It writes `highlightStart` and `highlightDuration` for automatic trimming.

### Smart Build

Build a new edit from a clip folder and music:

```powershell
python render.py smart-build examples/assets --music examples/assets/beat_music.wav --duration 8 --scene-duration 2 --style gaming_montage -o examples/generated/smart_build_project.json
python render.py render examples/generated/smart_build_project.json -o output/smart_build_preview.mp4 --quality preview --cache
```

This combines clip selection, beat analysis, beat sync, style presets, and JSON generation.

### Captions

Manual caption layers still work in JSON. Transcript captions can be added from `.txt`, `.srt`, or `.vtt`:

```powershell
python render.py captions examples/project.json examples/transcript.srt --mode word --style tiktok -o examples/generated/captioned_project.json
python render.py render examples/generated/captioned_project.json -o output/captioned_example.mp4 --quality preview
```

Caption modes:

- `phrase`: timed phrase captions.
- `word` / `word_by_word`: word-by-word captions.
- `karaoke`: word timing with karaoke-style color.

Caption styles:

- `default`
- `tiktok`
- `karaoke`

### Smart Layout

Layers can use layout hints instead of exact `x`/`y`:

```json
{
  "type": "text",
  "text": "Smart Layout",
  "layout": "lower_third",
  "safeZone": "title"
}
```

Supported layout concepts:

- safe zones: `title`, `action`, `none`, or numeric margins
- anchors: `center`, `upper_left`, `upper_right`, `bottom`
- center regions
- lower thirds
- split screen: `split_left`, `split_right`, `split_screen`
- picture-in-picture: `pip`
- grid cells with `grid`
- media auto-fit with `autoFit`

See `examples/smart_layout_project.json`.

### Style Presets

```powershell
python render.py style list
python render.py style apply examples/project.json red_black_aegis -o examples/generated/aegis_styled_project.json
```

Styles:

- `clean_cinematic`
- `gaming_montage`
- `red_black_aegis`
- `vaporwave`
- `minimal_tech`
- `horror_glitch`
- `luxury_promo`

Styles apply colors, text treatment, media contrast/brightness, default transitions, and selected layer effects.

### Render Optimizer

Scene-by-scene rendering is now backed by optional cache and resume:

```powershell
python render.py render examples/generated/smart_build_project.json -o output/smart_build_preview.mp4 --quality preview --cache
python render.py render examples/generated/smart_build_project.json -o output/smart_build_resume.mp4 --quality preview --cache --resume
```

Options:

- `--quality preview`: fast low-quality preview render with higher CRF and ultrafast encode preset.
- `--quality final`: high-quality default render.
- `--cache`: stores rendered scene clips in `output/.render_cache`.
- `--resume`: reuses matching cached scene clips after a failed or interrupted render.
- `--gpu`: tries `h264_nvenc` when available and falls back to CPU if unavailable.

### Render Report

Every render writes:

```text
output/render_report.json
```

The report includes duration, assets used, missing or failed assets, effects used, render time, output file size, warnings, quality mode, cache usage, and GPU usage.

## Export Presets

```text
youtube_1080p   1920x1080 60fps
tiktok_reels    1080x1920 60fps
shorts          1080x1920 60fps
square          1080x1080 30fps
discord_720p    1280x720 30fps compressed
cinematic_4k    3840x2160 24fps
```

Use a preset in JSON:

```json
{
  "exportPreset": "tiktok_reels",
  "project": {
    "width": 1080,
    "height": 1920,
    "fps": 60,
    "duration": 15,
    "background": "#000000"
  }
}
```

Or override at render time:

```powershell
python render.py render examples/project.json --preset discord_720p
```

## Templates

Available templates:

- `youtube_intro`
- `tiktok_reels_short`
- `gaming_montage`
- `product_promo`
- `lyric_video`
- `slideshow`
- `meme_edit`
- `tutorial_video`

Create a template project:

```powershell
python render.py template create gaming_montage -o examples/templates/gaming_montage.json
python render.py preview examples/templates/gaming_montage.json --generate-placeholders
python render.py render examples/templates/gaming_montage.json -o output/gaming_montage.mp4 --generate-placeholders
```

Each generated template includes `metadata.requiredAssets`, placeholder text, transition style, music/SFX slots, audio tracks, and an export preset.

## AI Generation Flow

The current `ai-generate` command is a local prompt interpreter. It does not call an external model yet, but it builds valid project JSON from plain English using templates, duration detection, theme detection, captions, fast-cut logic, and transition hints.

```powershell
python render.py ai-generate "Create a 20 second gaming montage with fast cuts, red black theme, captions, and bass drop transitions." -o examples/generated/gaming_prompt.json
python render.py validate examples/generated/gaming_prompt.json
python render.py render examples/generated/gaming_prompt.json -o output/ai_gaming_prompt.mp4 --generate-placeholders
```

Future work can swap the local generator for an API-backed model while keeping the same repair and validation gate.

## JSON Repair

Repair detects schema errors, prints what is wrong, applies safe defaults, validates again, and writes a fixed project.

```powershell
python render.py validate examples/bad_project.json
python render.py repair examples/bad_project.json -o examples/generated/bad_project.repaired.json
python render.py render examples/generated/bad_project.repaired.json --generate-placeholders
```

The render command can also repair first:

```powershell
python render.py render examples/bad_project.json --repair --generate-placeholders
```

## Preview Reports

Preview writes:

- `timeline_summary.json`
- `render_plan.txt`
- scene list
- layer list
- asset usage report
- missing asset report
- estimated timeline duration

```powershell
python render.py preview examples/project.json
python render.py preview examples/templates/gaming_montage.json --generate-placeholders -o output/gaming_preview
```

## Interactive Preview Before Export

Interactive preview creates a temporary playable MP4 and review assets without exporting the final video:

```powershell
python render.py interactive-preview examples/project.json -o output/interactive_preview --quality-mode balanced
python render.py interactive-preview examples/project.json -o output/interactive_preview_scene --quality-mode draft --scope scene --scene-id intro
```

Quality modes are `draft`, `proxy`, `balanced`, `high`, and `final_sim`. The desktop Preview tab uses this command to show cached preview playback, scene thumbnails, waveform display, current timestamp, estimated final duration, and timeline playhead. See [docs/INTERACTIVE_PREVIEW_MODE.md](docs/INTERACTIVE_PREVIEW_MODE.md).

The Preview tab also supports review control before export: timestamp markers, pause-and-edit scene changes, deterministic regeneration, A/B versions, notes, scene approvals, scene locks, exclusion from final export, and an export readiness gate. See [docs/PREVIEW_REVIEW_EDIT_CONTROL.md](docs/PREVIEW_REVIEW_EDIT_CONTROL.md).

Final preflight automation checks the approved preview and project before final export, scores pacing/readability/audio/brand/technical readiness, suggests repairs, and supports safe one-click fixes:

```powershell
python render.py final-preflight check examples/project.json -o output/final_preflight.json --format mp4
python render.py final-preflight repair examples/project.json -o output/project.preflight_repaired.json --mode all
```

See [docs/FINAL_REVIEW_PREFLIGHT.md](docs/FINAL_REVIEW_PREFLIGHT.md).

## Assets

Asset map values can point to files or folders:

```json
"assets": {
  "clip": "assets/gameplay.mp4",
  "music": "assets/song.wav",
  "media_folder_video": "assets"
}
```

When a folder is used, the resolver picks the first matching file for the layer type. See `examples/folder_asset_project.json`.

Missing assets produce clear errors. For testing, generate placeholders automatically:

```powershell
python render.py preview examples/templates/product_promo.json --generate-placeholders
python render.py render examples/templates/product_promo.json --generate-placeholders
```

## Working Examples

- `examples/project.json`: original renderer demo.
- `examples/folder_asset_project.json`: folder-based asset resolution.
- `examples/smart_layout_project.json`: smart layout zones.
- `examples/transcript.srt`: transcript input for caption generation.
- `examples/bad_project.json`: repair workflow input.
- `examples/generated/gaming_prompt.json`: prompt-to-JSON output.
- `examples/generated/bad_project.repaired.json`: repaired JSON output.
- `examples/generated/beat_synced_project.json`: beat-sync output.
- `examples/generated/captioned_project.json`: transcript caption output.
- `examples/generated/smart_build_project.json`: smart-build output.
- `examples/generated/phase8_hype_intro.json`: renderable motion-graphics hype intro.
- `examples/generated/phase8_cinematic_project.json`: cinematic enhancement output.
- `examples/generated/aegis_styled_project.json`: style preset output.
- `examples/broll_project.json`: B-roll placeholder workflow input.
- `examples/generated/broll_resolved_project.json`: resolved B-roll output.
- `examples/generated/director_gaming_project.json`: AI Director output.
- `output/asset_intelligence.json`: asset intelligence report.
- `output/storyboard_smoke/storyboard.json`: storyboard output.
- `output/project_package_smoke.zip`: package export smoke output.
- `examples/templates/*.json`: one generated JSON file per template.
- `output/timeline_summary.json` and `output/render_plan.txt`: preview outputs.
- `output/render_report.json`: most recent render report.
- `output/phase8_clip_understanding.json`, `output/phase8_audio_intel.json`, `output/phase8_project_analysis.json`: Phase 8 local intelligence reports.
- `output/phase9_workspace.json`, `output/phase9_review_report.json`, `output/phase9_asset_db_report.json`, `output/phase9_training_dataset.json`, `output/phase9_creator_analytics.json`, `output/phase9_local_policy.json`, `output/phase9_diagnostics.json`: Phase 9 ecosystem smoke outputs.
- `output/phase10_dependency_report.json`, `output/phase10_model_status.json`, `output/phase10_privacy_report.json`, `output/phase10_performance_dashboard.json`, `output/phase10_installer_manifest.json`: Phase 10 hardening outputs.
- `examples/demos/*.json`: bundled Phase 11 demo projects for gaming montage, cinematic trailer, TikTok edit, lyric video, and product promo.
- `examples/generated/phase11_refined_project.json` and `output/phase11_refined_preview.mp4`: Phase 11 refinement smoke output.
- `output/phase11_suggestions.json`, `output/phase11_integrity_report.json`, `output/phase11_cache_report.json`: Phase 11 quality, recovery, and cache reports.
- `examples/generated/cinematic_showcase_project.json`, `output/cinematic_showcase_analysis.json`, `output/cinematic_showcase_preview.mp4`: Cinematic Auto Showcase Mode smoke output.
- `output/final_architecture_audit.json`, `output/final_performance_profile.json`, `output/final_release_candidate_check.json`: finalization readiness reports.
- `output/finalization_smoke_render.mp4`: finalization render smoke output.
- `output/automatic-video-editor-finalization-portable.zip`: finalization portable CLI package.
- `desktop-app/release/Automatic Video Editor Setup 0.9.0.exe`: Windows release-candidate installer.
- `output/asset_database/assets.sqlite`: local SQLite asset index.
- `output/phase9_gaming.templatepack`: offline template pack smoke output.
- `output/final_video.mp4`, `output/gaming_montage.mp4`, `output/ai_gaming_prompt.mp4`, `output/folder_asset_example.mp4`, `output/beat_synced_example.mp4`, `output/captioned_example.mp4`, `output/smart_layout_example.mp4`, `output/smart_build_preview.mp4`, `output/phase8_cinematic_preview.mp4`: rendered smoke-test outputs.

## Phase 10 Local Hardening

Phase 10 keeps the product offline-capable and adds practical reliability tools:

```powershell
python render.py dependency-check -o output/phase10_dependency_report.json
python render.py model-manager status -o output/phase10_model_status.json
python render.py privacy-report -o output/phase10_privacy_report.json
python render.py performance-report -o output/phase10_performance_dashboard.json
python render.py installer prepare -o output/phase10_first_run_setup.json
python render.py installer manifest -o output/phase10_installer_manifest.json
```

Reliable rendering uses crash-safe partial files, logs each attempt, and can reuse cached scene renders:

```powershell
python render.py reliable-render examples/project.json -o output/phase10_reliable_render.mp4 --attempts 2 --quality preview
```

Recovery tools now support manual restore points, cleanup policies, and corrupted-project recovery:

```powershell
python render.py recovery restore-point examples/project.json --label before_ai_edit
python render.py recovery cleanup examples/project.json --keep 12
python render.py recovery recover-corrupt examples/project.json -o examples/generated/recovered.json
```

Plugin safety remains local-only:

```powershell
python render.py plugin audit
python render.py plugin disable sample_punch_zoom_transition
python render.py plugin enable sample_punch_zoom_transition
```

Bundled docs are available offline:

```powershell
python render.py docs list
python render.py docs show ffmpeg
python render.py docs show local-ai
python render.py docs show workflow-automation
python render.py docs show quality-feedback
python render.py docs show long-term-evolution
```

## Phase 11 Refinement

Phase 11 focuses on making existing workflows smoother and more professional:

```powershell
python render.py refine examples/project.json --preset premium_red_black -o examples/generated/phase11_refined_project.json
python render.py render examples/generated/phase11_refined_project.json -o output/phase11_refined_preview.mp4 --quality preview --cache --resume
python render.py suggest examples/generated/phase11_refined_project.json -o output/phase11_suggestions.json
```

Color pipeline presets and local LUT discovery:

```powershell
python render.py color list
python render.py color luts
python render.py color apply examples/project.json clean_cinematic -o examples/generated/phase11_color_project.json
```

Timeline and preview refinement:

```powershell
python render.py realtime-preview examples/generated/phase11_refined_project.json --time 4 --mode draft --layers all -o output/phase11_realtime
```

Creator profiles and large-project upkeep:

```powershell
python render.py profile create "Phase 11 Creator" -o examples/generated/phase11_creator_profile.json
python render.py profile apply examples/project.json examples/generated/phase11_creator_profile.json -o examples/generated/phase11_profile_project.json
python render.py cache report -o output/phase11_cache_report.json
python render.py cache cleanup --max-gb 20 --dry-run
```

Recovery and integrity checks:

```powershell
python render.py recovery integrity examples/generated/phase11_refined_project.json -o output/phase11_integrity_report.json
python render.py recovery relink project.json assets_folder -o examples/generated/project.relinked.json
```

Built-in polished demos:

```powershell
python render.py demo list
python render.py render examples/demos/product_promo.json -o output/demo_product_promo.mp4 --quality preview --cache
```

## Cinematic Auto Showcase Mode

Showcase Mode turns a raw desktop recording into a trailer-style product edit. It analyzes motion, click-like interaction spikes, scene/window changes, idle sections, focus regions, text-heavy moments, optional music beats, and then writes normal project JSON with title cards, captions, focus crops, camera movement, lighting, transitions, intro/outro, and optional music.

List modes:

```powershell
python render.py showcase --list-styles
```

Generate JSON only:

```powershell
python render.py showcase recording.mp4 --style auto --instructions "Make this feel like a premium cybersecurity tool with smooth zooms and red lighting" -o examples/generated/showcase_project.json
```

Generate and render:

```powershell
python render.py showcase examples/assets/gameplay.mp4 --music examples/assets/beat_music.wav --logo examples/assets/logo.png --style hacker_cyber --product-name "Aegis Troubleshooter" --duration 10 -o examples/generated/cinematic_showcase_project.json --analysis-output output/cinematic_showcase_analysis.json --spec-output output/cinematic_showcase_spec.json --score-output output/cinematic_showcase_score.json --advanced-output output/cinematic_showcase_advanced.json --render --render-output output/cinematic_showcase_preview.mp4 --quality preview --cache
```

Custom style profile:

```json
{
  "style": "premium_tech",
  "lighting": "soft_red_glow",
  "cameraMovement": "smooth",
  "pace": "medium_fast",
  "transitionIntensity": 0.6
}
```

Offline docs:

```powershell
python render.py docs show showcase
```

Phase 12 manual overrides:

```powershell
python render.py showcase examples/assets/gameplay.mp4 --overrides examples/showcase_overrides.json -o examples/generated/phase12_showcase_project.json --analysis-output output/phase12_showcase_analysis.json --spec-output output/phase12_showcase_spec.json --score-output output/phase12_showcase_score.json
```

## Advanced Cinematic Systems

The advanced systems pass upgrades project JSON with renderable Rec.709 color management, motion-derived camera keyframes, semantic workflow understanding, temporal editing memory, typography/readability improvements, audio mix settings, render-graph metadata, GPU fallback planning, asset scoring, license warnings, deterministic fingerprints, and AI explainability.

Apply it to any existing project:

```powershell
python render.py advanced examples/project.json -o examples/generated/project.advanced_systems.json --report output/project_advanced_systems_report.json
```

See [docs/ADVANCED_SYSTEMS.md](docs/ADVANCED_SYSTEMS.md).

## MVP Roadmap

The product is now narrowed back to a practical MVP path. Build vertically, keep JSON as the source of truth, use FFmpeg first, and require every milestone to compile and render a real MP4.

```powershell
python render.py docs show mvp
python render.py validate examples/project.json
python render.py render examples/project.json -o output/mvp_0_1.mp4 --quality preview --cache
python render.py quick-create examples/assets/gameplay.mp4 --music examples/assets/beat_music.wav --logo examples/assets/logo.png --title "Aegis Troubleshooter" --caption "Scans runtimes, launch blockers, anti-cheat conflicts, and Windows security settings." --style red_black --duration 8 -o examples/generated/mvp_0_1_quick_create.json --render --render-output output/mvp_0_1_quick_create.mp4 --quality preview --cache
```

See [docs/MVP_ROADMAP.md](docs/MVP_ROADMAP.md) and [docs/mvp/VERSION_0_1_IMPLEMENTATION_PLAN.md](docs/mvp/VERSION_0_1_IMPLEMENTATION_PLAN.md).

## Foundation Systems

Use the foundation pass when a project needs frame-accurate timing, non-destructive metadata, history snapshots, proxies, local task files, cache buckets, accessibility checks, hardware reports, and recovery journals before more advanced editing work.

```powershell
python render.py foundation-pass examples/generated/mvp_0_1_quick_create.json -o examples/generated/mvp_0_1_quick_create.foundation.json --report output/foundation_report.json --generate-proxies --benchmark
python render.py render examples/generated/mvp_0_1_quick_create.foundation.json -o output/foundation_mvp_render.mp4 --quality preview --cache
```

See [docs/FOUNDATION_SYSTEMS.md](docs/FOUNDATION_SYSTEMS.md).

## Finalization

The finalization pass adds production-readiness commands for architecture cleanup, profiling, release checks, installer builds, plugin API documentation, schema documentation, and developer workflow guidance.

Audit architecture boundaries, documentation coverage, plugins, and technical-debt hotspots:

```powershell
python render.py architecture-audit -o output/final_architecture_audit.json
```

Profile the core workflow without forcing a full final export:

```powershell
python render.py profile-run examples/project.json -o output/final_performance_profile.json
```

Run the release-candidate gate across sample projects, integrity checks, dependencies, plugin safety, architecture audit, and performance profiling:

```powershell
python render.py release-check -o output/final_release_candidate_check.json
```

Build local release artifacts:

```powershell
python render.py installer portable -o output/automatic-video-editor-finalization-portable.zip
cd desktop-app
npm run typecheck
npm run build
npm run build:installer
```

Expanded offline docs:

```powershell
python render.py docs show developer
python render.py docs show plugin-api
python render.py docs show schema
python render.py docs show beginner
python render.py docs show advanced
python render.py docs show workflow-automation
python render.py docs show quality-feedback
python render.py docs show long-term-evolution
python render.py docs show release
python render.py docs show changelog
```

## Troubleshooting FFmpeg

The renderer looks for FFmpeg in this order:

1. `FFMPEG_BINARY` environment variable
2. `ffmpeg` on `PATH`
3. bundled binary from `imageio-ffmpeg`

If FFmpeg is missing:

```powershell
python -m pip install -r requirements.txt
```

If a render fails, rerun with debug logs and keep temp files:

```powershell
python render.py render examples/project.json --keep-temp --log-level DEBUG
```

If assets are missing, run preview first:

```powershell
python render.py preview examples/project.json
```

If JSON is invalid, repair before render:

```powershell
python render.py repair examples/bad_project.json
```

## Project Structure

```text
automatic-video-editor/
  render.py
  requirements.txt
  src/
    ai/
    analytics/
    assets/
    audio/
    broll/
    cinematic/
    captions/
    clips/
    color/
    datasets/
    docs/
    ecosystem/
    effects/
    engines/
    evolution/
    feedback/
    finalization/
    history/
    installer/
    intelligence/
    layout/
    local_ai/
    mvp/
    packs/
    parser/
    plugins/
    presets/
    preview/
    project_packaging/
    reports/
    renderer/
    repair/
    recovery/
    refinement/
    schema/
    security/
    showcase/
    social/
    stability/
    storyboard/
    styles/
    templates/
    transitions/
    utils/
    workers/
    workflow/
    workspace/
  desktop-app/
    electron/
    src/
    package.json
  examples/
    project.json
    bad_project.json
    broll_project.json
    folder_asset_project.json
    generated/
    templates/
  plugins/
  docs/
  output/
  README.md
```
