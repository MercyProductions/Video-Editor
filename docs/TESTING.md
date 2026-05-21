# Testing

The project uses small local smoke tests first. They avoid new test dependencies and focus on the MVP path: JSON validation, clear asset errors, quick-create JSON generation, isolated preview renders, and quality checks.

## Fast Backend Smoke Tests

These cover schema validation, readable missing-asset errors, quick-create JSON generation, and default quality checks without rendering video.

```powershell
python -m unittest tests.test_smoke
```

## Render Smoke Tests

These render temporary MP4 files, inspect them with media probing, and assert output duration stays close to the project duration.

```powershell
python -m unittest tests.test_render_smoke
```

## Full Backend Smoke Tests

```powershell
python -m unittest discover -s tests
```

## Desktop Checks

```powershell
cd desktop-app
npm run typecheck
npm run test:unit
npm run build
```

For all desktop checks in one command:

```powershell
cd desktop-app
npm run verify
```

## Full Local Release Gate

```powershell
python render.py release-check -o output/release_candidate_check.json
```

For the top-level local verification wrapper:

```powershell
python scripts/verify_local.py
```

The release gate now includes Python compile, backend smoke tests, JSON/demo validation, quality check, preview render duration check, final render duration check, desktop typecheck, desktop unit tests, and desktop build. The backend smoke suite includes render-backed tests that write MP4 files only into temporary folders.
