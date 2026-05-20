# Quality Feedback Loops

Phase 17 adds local-only feedback loops so successful and unsuccessful edits can improve future generations without telemetry, accounts, or cloud services.

## Render Review

After rendering, rate the finished edit:

```powershell
python render.py feedback review examples/generated/phase16_workflow_rendered/v01_serious_cinematic/project.json --video examples/generated/phase16_workflow_rendered/v01_serious_cinematic/final_video.mp4 --plan examples/generated/phase16_workflow_rendered/v01_serious_cinematic/content_plan.json --profile "Aegis Creator" --pacing 4 --readability 4 --transitions 3 --cinematic 5 --hook 5 --captions 4 --polish 4 --note "Strong hook and style; reduce motion next time."
```

Reviews are stored under `feedback/reviews/<profile>/` and include ratings, project fingerprint, style consistency, hook effectiveness, self-analysis, preference hints, and explanations.

## Render Self-Analysis

Analyze a rendered edit:

```powershell
python render.py feedback analyze examples/generated/phase16_workflow_rendered/v01_serious_cinematic/project.json --video examples/generated/phase16_workflow_rendered/v01_serious_cinematic/final_video.mp4 -o output/phase17_self_analysis.json
```

The report checks pacing, caption density, repetitive transitions, dead/static sections, excessive motion, overprocessed visuals, readability issues, black-frame events, and frozen-frame events.

## Style Consistency

Score whether an edit matches a creator profile:

```powershell
python render.py feedback consistency examples/generated/phase16_workflow_rendered/v01_serious_cinematic/project.json --profile "Aegis Creator" -o output/phase17_style_consistency.json
```

The score covers pacing, branding, transition consistency, and lighting consistency.

## Hook Effectiveness

Estimate short-form hook strength:

```powershell
python render.py feedback hook --project examples/generated/phase16_workflow_rendered/v01_serious_cinematic/project.json --plan examples/generated/phase16_workflow_rendered/v01_serious_cinematic/content_plan.json -o output/phase17_hook_effectiveness.json
```

The report includes hook intensity, pacing momentum, viewer retention potential, readability speed, visual overload risk, and recommendations.

## AI Improvement Signals

Track creator corrections:

```powershell
python render.py feedback ai-event "Aegis Creator" --project examples/generated/phase16_workflow_rendered/v01_serious_cinematic/project.json --scene-regenerated feature_3 --transition-removed fadeToBlack --caption-edited hook --section-locked hook --note "Kept hook, removed repeated fade."
```

The engine tracks regenerated scenes, removed transitions, edited captions, and locked sections. Future workflow batches can use the learned creator identity guidance.

## Creator Identity Learning

Build or refresh the local creator identity model:

```powershell
python render.py feedback learn "Aegis Creator" -o output/phase17_creator_identity.json
python render.py feedback identity "Aegis Creator"
```

The identity model stores pacing rhythm, transition philosophy, motion style, caption behavior, style fingerprint, AI improvement signals, and generation guidance.

## Local Training Dataset

Export approved edits for future local fine-tuning:

```powershell
python render.py feedback dataset "Aegis Creator" -o output/phase17_training_dataset --min-rating 4
```

The dataset folder contains approved edits, pacing maps, transition patterns, successful timelines, style fingerprints, and a manifest. All files remain local.

## Desktop App

The Product tab includes a Quality Feedback Loop panel:

- Run self-analysis on the current project and rendered preview.
- Rate pacing, readability, transitions, cinematic quality, hook strength, captions, and polish.
- Save a local render review.
- Refresh the creator identity model.

## Local-First Guarantees

- No telemetry.
- No cloud training.
- No account required.
- Feedback is stored as local JSON.
- The creator can inspect, delete, or export every learned artifact.
