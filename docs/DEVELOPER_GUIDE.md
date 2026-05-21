# Developer Guide

Automatic Video Editor is local-first. The JSON project is the source of truth, and the renderer is FFmpeg-first.

Core boundaries:

- `parser/` validates and normalizes project JSON.
- `renderer/` renders scenes, transitions, audio, cache-aware output, and reports.
- `effects/` owns FFmpeg filter snippets.
- `assets/` resolves, analyzes, and indexes media.
- `local_ai/`, `ai/`, and `content/` generate and improve JSON locally.
- `desktop-app/` edits JSON and queues renders; it should not become a second editing format.
- `finalization/` contains audit, profiling, and release-readiness tools.

Before release work:

```powershell
python -m compileall src
python -m unittest discover -s tests
cd desktop-app
npm run typecheck
npm run test:unit
npm run build
```

Release checks:

```powershell
python render.py architecture-audit -o output/architecture_audit.json
python render.py profile-run examples/project.json -o output/performance_profile.json
python render.py release-check -o output/release_candidate_check.json
```

One-command local verification:

```powershell
python scripts/verify_local.py
```

See [TESTING.md](TESTING.md) for the current smoke test and release gate commands.

Development rules:

- Keep edits metadata-driven and non-destructive.
- Prefer adding renderer support to existing layer/effect fields over inventing new project formats.
- Validate every generated example JSON.
- Keep plugin execution isolated until a permission model explicitly allows execution.
