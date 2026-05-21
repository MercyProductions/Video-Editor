# Changelog

## 0.9.0 Internal Verification Checkpoint

- Verified the current local-first baseline with `python scripts\verify_local.py`.
- Current release gate reports `ready=true`, 24 checks, 0 failed.
- Release report path: `output\local_verify_release_check.json`.
- Added backend smoke tests, desktop helper tests, and a top-level local verification script.
- Added desktop `npm run verify` for typecheck, unit tests, and production build.
- Split large desktop surfaces into focused components and extracted Electron media/history helpers.
- This checkpoint is an internal engineering baseline; packaged installer/ZIP verification remains a later release gate.

## 0.9.0 Release Candidate

- Added finalization audit, profiling, and release-candidate checks.
- Expanded bundled documentation for developers, plugins, schema, tutorials, and release process.
- Improved local AI status by routing through the local model manager.
- Improved asset indexing by reusing unchanged SQLite rows and prioritizing assets with previews in search results.
- Updated engine registry to reflect render, AI, asset, plugin, export, and quality engine boundaries.
- Added sample local plugin manifests for transition, effect, and template extension points.

## 0.8.0 Phase 11

- Added cinematic refinement pass, color pipeline presets, LUT folder, cache reports, integrity checks, and polished demos.
- Improved timeline snapping/ripple UX and realtime preview quality modes.

## 0.7.0 Phase 10

- Added local model manager, dependency checker, privacy report, reliable render retry, installer manifests, portable ZIP, and desktop hardening panel.
