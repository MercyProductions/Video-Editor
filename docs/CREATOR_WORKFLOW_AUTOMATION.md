# Creator Workflow Automation

Phase 16 turns one-off generation into a repeatable local creator workflow. Everything stays on disk: creator profiles, workflow recipes, batch outputs, scheduled task manifests, local memory, metrics, and dashboard reports.

## Creator Profiles

Create a reusable profile for brand defaults, caption style, intro/outro behavior, pacing, preferred transitions, export defaults, and CTA style:

```powershell
python render.py workflow profile "Aegis Creator" -o profiles/aegis_creator.creator-profile.json
```

Profiles are normal JSON files. They can be applied through existing profile commands or referenced by workflow pipelines.

## Reusable Pipelines

Save a repeatable workflow recipe:

```powershell
python render.py workflow pipeline-create "Cybersecurity Tool Demo" --preset cybersecurity_tool_demo --profile profiles/aegis_creator.creator-profile.json -o workflows/pipelines/cybersecurity_tool_demo.workflow.json
python render.py workflow pipeline-list
python render.py workflow pipeline-show workflows/pipelines/cybersecurity_tool_demo.workflow.json
```

Built-in presets:

- `youtube_short_product_showcase`
- `cybersecurity_tool_demo`
- `gaming_montage`
- `minimal_saas_promo`

Each pipeline stores generation mode, tone, style, duration, pacing, structure, effects, creator profile defaults, and export package defaults.

## Batch Generation

Generate multiple local variants from one workflow:

```powershell
python render.py workflow batch workflows/pipelines/cybersecurity_tool_demo.workflow.json "Create shorts for Automatic Troubleshooter showing missing runtimes, launch blockers, anti-cheat conflicts, and Windows security settings" --assets examples/assets --music examples/assets/beat_music.wav --logo examples/assets/logo.png --versions 2 -o examples/generated/phase16_workflow_batch
```

Each variant gets its own folder with `content_plan.json`, review files, and `project.json`. Add `--render --quality preview` when you want each variant rendered immediately.

## Local Scheduled Tasks

Create local task manifests for repeatable maintenance and overnight work:

```powershell
python render.py workflow task-create "Nightly cache cleanup" cache_cleanup --run-at overnight --priority 3 --cmd "cache cleanup --max-gb 4 --dry-run"
python render.py workflow task-list
python render.py workflow task-run --force --limit 1
```

Scheduled tasks run `render.py` locally. They do not use cloud workers or remote machines.

## Creator Memory

Record successful edits and manual preferences:

```powershell
python render.py workflow memory-update "Aegis Creator" --project examples/generated/phase16_workflow_batch/v01_serious_cinematic/project.json --plan examples/generated/phase16_workflow_batch/v01_serious_cinematic/content_plan.json --rating reuse --note "Good cybersecurity pacing" --prefer motionIntensity=medium_fast
python render.py workflow memory-show --profile "Aegis Creator"
```

The memory layer stores local preference events and learned hints such as preferred style, hook, transition, and manual overrides. It is simple JSON under `workflows/memory/`.

## Asset Reuse Intelligence

Summarize reused clips, hooks, transitions, styles, and creator preferences:

```powershell
python render.py workflow asset-reuse --project examples/generated/phase16_workflow_batch/v01_serious_cinematic/project.json -o output/phase16_asset_reuse.json
```

The report combines the SQLite asset database, project asset usage, local metrics, and creator memory.

## Production Dashboard

Generate a local production dashboard:

```powershell
python render.py workflow dashboard --project examples/generated/phase16_workflow_batch/v01_serious_cinematic/project.json -o output/phase16_dashboard.json
```

The dashboard includes recent renders, queued/running local jobs, output/export/cache size, asset database health, duplicate asset count, project quality health, render success rate, metrics, and workflow warnings. The Electron Product tab exposes the same dashboard through the Production Dashboard panel.

## Local-First Guarantees

- No accounts.
- No telemetry.
- No cloud rendering.
- No remote sync.
- All profiles, pipelines, task manifests, memory, reports, generated projects, and dashboards are normal local files.
