# Project Roadmap Review

Generated: 2026-05-21

Project root: `C:\Users\gabri\Desktop\Aegis\Tools\Kioson\automatic-video-editor`

## Executive Summary

Automatic Video Editor is now in a much better state than the first review. The core local-first path is verified: the Python/FFmpeg engine validates projects, runs smoke tests, performs quality checks, renders preview and final MP4 outputs, and the Electron desktop app passes typecheck, unit tests, and production build.

The remaining work is not "make it work at all." The remaining work is to make it boringly reliable: reduce the oversized modules, broaden tests beyond the happy-path smoke project, prove the desktop workflow from launch to rendered output, package the app, and label advanced systems honestly until each one has a smoke test and a real output artifact.

## Current Verified State

Fresh review commands run on 2026-05-21, including the latest Phase 1 renderer scene-planning slice:

```powershell
python -m compileall -q src render.py
python render.py validate examples\project.json
python render.py examples\project.json -o output\phase1_renderer_scene_extract_smoke.mp4 --quality preview --cache
python render.py examples\project.json -o output\phase1_renderer_scene_uncached_smoke.mp4 --quality preview
python -m unittest discover -s tests
python render.py architecture-audit -o output\phase1_renderer_scene_architecture_audit.json
python scripts\verify_local.py
```

Results:

- Backend smoke tests: 9 passed.
- Release check: `ready=true`, 24 checks, 0 failed.
- Quality check on `examples/project.json`: 0 issues.
- Preview render: 10.0s expected, 10.0s actual, 0.0s delta.
- Final render: 10.0s expected, 10.0s actual, 0.0s delta.
- Desktop verify: typecheck, unit tests, Electron build, and Vite build passed.
- Dependency summary: ready, 0 warnings.
- Architecture audit: 156 Python files, 59 Python packages, 33 docs, 3 plugins, 1 warning.
- Architecture warning: 12 large functions still need future refactoring attention.

Important current file sizes:

- `desktop-app/src/App.tsx`: 11,446 lines.
- `src/main.py`: 1,970 lines.
- `desktop-app/electron/main.ts`: 1,884 lines.
- `src/cli_parser.py`: 1,170 lines.
- `src/renderer/renderer.py`: 445 lines.
- `desktop-app/electron/renderQueue.ts`: 426 lines.
- `desktop-app/electron/projectStore.ts`: 240 lines.
- `src/renderer/scene.py`: 278 lines.
- `src/workflow/cli.py`: 205 lines.
- `src/feedback/cli.py`: 157 lines.
- `src/renderer/audio.py`: 146 lines.
- `src/renderer/mux.py`: 133 lines.
- `src/finalization/release.py`: 217 lines.
- `src/quality/checker.py`: 183 lines.
- `desktop-app/electron/history.ts`: 110 lines.
- `desktop-app/electron/media.ts`: 45 lines.
- `desktop-app/electron/engine.ts`: 33 lines.

## What Is Already Done

- Desktop TypeScript marker errors are fixed.
- `npm run typecheck` passes.
- Backend smoke tests exist under `tests/`.
- Desktop helper tests exist through `desktop-app/scripts/run-unit-tests.cjs`.
- `npm run verify` runs desktop typecheck, unit tests, and build.
- `python scripts\verify_local.py` runs the local release verification path.
- `release-check` now includes Python compile, backend tests, quality check, preview render, final render, desktop typecheck, desktop unit tests, and desktop build.
- The default smoke project quality warning is cleared.
- README, testing docs, developer docs, and release checklist now point toward the verified workflow.
- `desktop-app/src/App.tsx` has been partially split into focused React components:
  - `VisualTimeline`
  - `PreviewWindow`
  - `AssetLibrary`
  - `JsonEditor`
  - `HelpPanels`
- Large desktop UI panels are lazy-loaded, and the main Vite chunk is now under the prior warning threshold.
- Electron media helpers moved to `desktop-app/electron/media.ts`.
- Electron history/version helpers moved to `desktop-app/electron/history.ts`.

## What Still Needs Done

### Product Reliability

- Prove the full creator path in the desktop app: open/create project, validate, preview render, final render, inspect output, and recover from failure.
- Add a real desktop end-to-end smoke test or a repeatable manual script with screenshots and expected states.
- Confirm the UI never silently writes a project JSON shape that the CLI cannot validate.
- Make render progress, logs, failure messages, output paths, and retry behavior consistent across the app.
- Make autosave and recovery flows explicit, testable, and safe.

### Architecture

- Continue splitting `desktop-app/src/App.tsx`; it is still the largest risk point at 11,446 lines.
- Continue splitting `desktop-app/electron/main.ts`; the remaining IPC orchestration, window lifecycle, panel management, and health/diagnostic glue still need smaller ownership boundaries.
- Continue slimming `src/main.py`; it is no longer in the architecture-audit hotspot list, but it is still the central top-level CLI surface.
- Keep `src/cli_parser.py` grouped by command family as new commands are added so parser construction does not become another oversized control point.
- Continue renderer cleanup around transition composition and golden render coverage; `src/renderer/renderer.py` is no longer in the architecture-audit hotspot list.
- Move pure helpers into typed/tested modules before moving behavior-heavy code.

### Tests

- Add golden render projects for transitions, captions, title cards, trims, overlays, audio fades, and vertical export.
- Add render cache regression tests.
- Add generator tests for every project-producing command.
- Add asset repair/relink tests.
- Add packaged-app smoke tests once packaging is wired.
- Add FFprobe duration checks beyond the default smoke project.
- Add desktop tests for render queue serialization, project health summaries, autosave/recovery, and preview review state.

### Render Quality And Performance

- Track preview and final render timings over multiple fixture projects.
- Verify cache keys include every render-affecting field.
- Add clear warnings for GPU fallback, unsupported codecs, variable frame rate media, odd dimensions, and audio sample-rate issues.
- Improve audio checks for loudness, clipping, fades, loops, and sync.
- Make render reports map warnings to concrete UI actions.

### Media And Project Management

- Add robust media relink flows in CLI and desktop.
- Add duplicate detection and missing asset repair UX.
- Add portable project package export/import smoke tests.
- Confirm a moved project can still validate and render after import.
- Make asset database failure non-fatal for basic rendering.

### Local AI And Generation

- Keep deterministic template generation separate from local model generation.
- Require every generator to emit valid project JSON under tests.
- Preserve locked scenes during regeneration.
- Add confidence and reason fields consistently for suggestions.
- Block final-quality render when generated content requires review.
- Make local AI absence produce graceful deterministic fallback output.

### Packaging And Distribution

- Make `npm run dist` and `npm run build:installer` part of release verification or a separate packaging gate.
- Confirm packaged Electron can find `render.py`, `src`, examples, docs, LUTs, and FFmpeg dependencies.
- Build and test both NSIS installer and ZIP output.
- Test packaged app on a clean user profile.
- Ensure first-run dependency checks are visible and repairable.

### Documentation And Product Truth

- Keep README focused on the stable path first.
- Maintain a command matrix with status, inputs, outputs, and smoke-tested status.
- Mark advanced systems as experimental until each has a smoke command and output artifact.
- Keep `docs/MVP_ROADMAP.md` as the near-term product constraint.
- Avoid presenting aspirational systems as production-ready.

## Roadmap From Here

## Phase 0: Checkpoint The Verified Baseline

Goal:
Preserve the current green baseline before more refactors.

Work:

- Review the current working tree and group changes into sensible commits.
- Keep generated outputs out of commits unless they are intentional fixtures.
- Confirm `python scripts\verify_local.py` passes immediately before the checkpoint.
- Record the release check output path in release notes or the changelog.
- Decide whether the next release is an internal engineering release or a user-facing desktop build.

Acceptance:

- A clean commit or branch checkpoint exists.
- The roadmap, README, testing docs, and release checklist all describe the same verified state.
- Local verification still reports `ready=true`.

Phase 0 checkpoint status:

- Checkpoint type: internal engineering baseline, not a packaged user release.
- Generated output folders are ignored by Git: `output/`, `desktop-app/dist/`, `desktop-app/dist-electron/`, `desktop-app/.test-dist/`, and `desktop-app/release/`.
- Changelog now records the release check path: `output\local_verify_release_check.json`.
- Current verification command: `python scripts\verify_local.py`.
- Commit grouping recommendation:
  - verification and release gates
  - desktop component/module extraction
  - docs and roadmap truth updates

## Phase 1: Finish Architecture Risk Reduction

Goal:
Make the main change points small enough to modify without fear.

Work:

- Extract Electron render queue handling from `desktop-app/electron/main.ts`.
- Extract Electron engine command execution and log parsing from `desktop-app/electron/main.ts`.
- Extract Electron settings/recovery/project I/O helpers into dedicated modules.
- Continue splitting `desktop-app/src/App.tsx` into app shell, beginner flow, render/export, diagnostics, and settings surfaces.
- Split `src/main.py` parser setup by command group while keeping CLI command names stable.
- Extract renderer filter graph building and audio/mux helpers from `src/renderer/renderer.py`.
- Add focused unit tests for each new pure helper module.

Acceptance:

- `App.tsx`, Electron `main.ts`, and `src/main.py` trend down in size.
- `python scripts\verify_local.py` still passes after each extraction.
- No IPC channel names or CLI command names change unless intentionally documented.

Phase 1 progress:

- Extracted Python engine command execution into `desktop-app/electron/engine.ts`.
- Extracted Electron render queue state, render process spawning, progress parsing, cancellation, retry, priority, delivery-package creation, queue serialization, and default render output naming into `desktop-app/electron/renderQueue.ts`.
- Kept renderer-facing IPC channel names unchanged: `render:start`, `render:queue`, `render:pause`, `render:resume`, `render:cancel`, `render:retry`, and `render:priority`.
- Updated project health checks to ask the render queue controller for failed render count instead of reading queue internals.
- Reduced `desktop-app/electron/main.ts` from 2,270 lines to 1,914 lines.
- Current verification after this slice: desktop `npm run verify` passes.
- Extracted recent projects, project file read/write, temporary project paths, settings normalization/persistence, session crash markers, and recovery snapshot storage into `desktop-app/electron/projectStore.ts`.
- Kept project, recent, settings, recovery, and render IPC channel names stable while moving storage behavior behind the project store.
- Reduced `desktop-app/electron/main.ts` further from 1,914 lines to the current 1,884 lines after later wiring.
- Current verification after this slice: desktop `npm run verify` passes.
- Extracted CLI command registration and parser construction from `src/main.py` into `src/cli_parser.py`.
- Kept `COMMANDS` and `build_parser()` behavior stable, including the legacy default-to-render path for unrecognized first positional input.
- Reduced `src/main.py` from 3,082 lines to 2,202 lines before the workflow/feedback CLI extraction.
- Initial parser extraction moved the CLI setup hotspot into `src/cli_parser.py`; the next pass split that hotspot by command family.
- Current verification after this slice: Python compile, CLI help, project validation, and backend smoke tests pass.
- Split `src/cli_parser.py::build_parser` into focused command-family registration helpers while keeping the parser output and command names stable.
- Architecture audit large-function count dropped from 19 to 18; `build_parser()` is no longer one of the reported hotspots.
- Current verification after this slice: Python compile, CLI help, project validation, nested `template create`, backend smoke tests, and architecture audit pass.
- Replaced the long `src/main.py::main` command `if` chain with a `_COMMAND_HANDLERS` dispatch table.
- Verified the dispatch table matches `COMMANDS`: 84 handlers, 84 parser commands, no missing commands, no extra handlers.
- Confirmed CLI help output is unchanged compared with the parser-split baseline.
- Architecture audit large-function count dropped from 18 to 17; `main()` is no longer one of the reported hotspots.
- Remaining `src/main.py` audit hotspots are now `_cmd_workflow` at 101 lines and `_cmd_feedback` at 93 lines.
- Current verification after this slice: Python compile, CLI help diff, handler coverage check, project validation, nested `template create`, backend smoke tests, architecture audit, and `python scripts\verify_local.py` all pass.
- Extracted workflow subcommand routing from `src/main.py` into `src/workflow/cli.py`.
- Extracted feedback subcommand routing from `src/main.py` into `src/feedback/cli.py`.
- Kept the top-level `workflow` and `feedback` command names stable while replacing the oversized handlers with tiny delegating wrappers.
- Verified the moved command paths with `workflow pipeline-list` and `feedback analyze examples\project.json`.
- Confirmed CLI help output is unchanged compared with the dispatch-table baseline.
- Reduced `src/main.py` from 2,202 lines to 1,970 lines.
- Architecture audit large-function count dropped from 17 to 15; `src/main.py` no longer appears in the reported hotspots.
- Current verification after this slice: Python compile, CLI help diff, handler coverage check, moved workflow/feedback command smoke checks, project validation, backend smoke tests, architecture audit, and `python scripts\verify_local.py` all pass.
- Extracted audio mix rendering from `src/renderer/renderer.py` into `src/renderer/audio.py`.
- Extracted output mux/container branching from `src/renderer/renderer.py` into `src/renderer/mux.py`.
- Kept `VideoRenderer._render_audio()` and `VideoRenderer._mux()` as small delegating methods, preserving the render flow and output behavior.
- Verified the moved renderer paths with a cached preview render of `examples/project.json` and a template creation smoke.
- Reduced `src/renderer/renderer.py` from 826 lines to 624 lines.
- Architecture audit large-function count dropped from 15 to 13; `_render_audio()` and `_mux()` are no longer reported hotspots.
- Remaining renderer audit hotspot is `VideoRenderer._render_scene()` at 165 lines.
- Current verification after this slice: Python compile, project validation, preview render smoke, nested `template create`, backend smoke tests, architecture audit, and `python scripts\verify_local.py` all pass.
- Extracted scene input planning, scene filter graph composition, media overlay planning, caption filters, and post-scene filters from `src/renderer/renderer.py` into `src/renderer/scene.py`.
- Kept `VideoRenderer._render_scene()` responsible for cache lookup, FFmpeg execution, GPU fallback, and scene cache writes.
- Verified the moved scene planner with both cached and uncached preview renders of `examples/project.json`.
- Reduced `src/renderer/renderer.py` from 624 lines to 445 lines.
- Architecture audit large-function count dropped from 13 to 12; `src/renderer/renderer.py` no longer appears in the reported hotspots.
- Current verification after this slice: Python compile, project validation, cached and uncached preview render smokes, backend smoke tests, architecture audit, and `python scripts\verify_local.py` all pass.

## Phase 2: Prove The Desktop Creator Workflow

Goal:
Make the desktop app dependable for a non-terminal user.

Work:

- Define the golden user journey: create/open project, validate, preview render, final render, open output.
- Add visible validation state before render.
- Standardize render progress, logs, output path display, cancellation, and retry controls.
- Add "Open last output" and "Open project folder" commands.
- Align project health summaries with backend diagnostics.
- Add manual QA steps or automated Electron/Playwright coverage for the journey.
- Test autosave and restore confirmation without risking source project edits.

Acceptance:

- A user can complete the core workflow without editing JSON manually.
- Failed renders show a clear next action.
- Desktop app behavior matches CLI validation and render behavior.

## Phase 3: Build A Golden Render Suite

Goal:
Catch render regressions before they reach users.

Work:

- Add fixture projects for cuts, crossfades, fades, captions, title cards, overlays, trimmed video, audio fades, and vertical export.
- Add FFprobe duration assertions for every golden fixture.
- Add render report assertions for warnings, cache usage, assets, output path, and duration.
- Add cache invalidation tests that change render-affecting fields.
- Add a slower optional render suite separate from the fast smoke suite.

Acceptance:

- The fast suite stays quick enough for normal development.
- The golden render suite proves important output features with actual MP4s.
- Duration tolerance and warning behavior are documented.

## Phase 4: Harden Media And Project Portability

Goal:
Make real user media less fragile.

Work:

- Add CLI and desktop asset relink flows.
- Add missing asset repair UX.
- Add duplicate asset detection.
- Add media compatibility checks for VFR, unsupported codecs, odd dimensions, missing audio, and sample-rate mismatches.
- Add package export/import tests.
- Confirm projects can move folders and still render after relink/import.

Acceptance:

- Missing assets can be fixed without hand-editing JSON.
- Portable project export/import is smoke-tested.
- Asset database issues do not block basic rendering.

## Phase 5: Improve Render Quality And Performance

Goal:
Make output quality and render time predictable.

Work:

- Benchmark preview and final renders across golden fixtures.
- Improve cache hit/miss reporting.
- Verify GPU fallback behavior and warnings.
- Add audio loudness, clipping, fade, loop, and sync checks.
- Add media normalization guidance and UI-facing warnings.
- Make quality-check issues map to clear user actions.

Acceptance:

- Preview render is consistently faster than final render.
- Render reports identify performance, cache, warnings, and asset usage clearly.
- Quality warnings are actionable in CLI and desktop.

## Phase 6: Control Local AI And Generation

Goal:
Keep generation useful, reviewable, and deterministic enough to trust.

Work:

- Add tests for prompt-to-video, content-generate, auto-template, showcase, and social repurpose outputs.
- Ensure every generator writes valid project JSON.
- Preserve locked scenes during regeneration.
- Add confidence/reason fields consistently.
- Add approval gates before final render for generated content.
- Ensure no local model installed still gives a deterministic fallback.

Acceptance:

- Generated projects validate without hand edits.
- Locked user edits survive regeneration.
- Final render is blocked when generated content still requires review.

## Phase 7: Package And Distribute

Goal:
Prepare a desktop build that can be handed to another person.

Work:

- Run and fix `npm run dist`.
- Run and fix `npm run build:installer`.
- Verify bundled engine paths in packaged Electron.
- Test packaged app with a clean user profile.
- Confirm packaged app can validate and render `examples/project.json`.
- Add first-run dependency checks and repair instructions.
- Decide default output folder behavior for Windows users.

Acceptance:

- ZIP and installer builds are reproducible.
- Packaged app launches and renders a bundled project.
- Packaging steps are part of the release checklist.

## Phase 8: Tighten Documentation And Release Truth

Goal:
Make the docs tell the truth at a glance.

Work:

- Add a command matrix:
  - command
  - status
  - inputs
  - outputs
  - smoke-tested yes/no
- Update `docs/MVP_ROADMAP.md` with verified completion status.
- Keep advanced systems behind clearly marked experimental sections.
- Add troubleshooting entries for packaging, desktop build, and render dependency issues.
- Add release notes only for features that passed smoke verification.

Acceptance:

- A new developer can identify the stable path in five minutes.
- A creator can follow one path from project creation to MP4 output.
- No unverified system is described as stable.

## Phase 9: Promote Advanced Systems Carefully

Goal:
Expand only after the core is stable.

Work:

- Keep plugin execution manifest-only until isolation and permission prompts are tested.
- Keep cloud, telemetry, marketplace, and remote rendering out of scope unless explicitly re-chartered.
- Promote advanced workflows only after they pass the same smoke standard as the MVP:
  - input asset
  - generated or edited JSON
  - validation
  - preview/final render
  - report
  - docs
- Add capability flags for experimental desktop panels.

Acceptance:

- Advanced features cannot silently break the core render path.
- Experimental features are labeled and isolated.
- The product remains local-first.

## Suggested 30-Day Execution Plan

### Week 1

- Checkpoint the current verified baseline.
- Extract Electron render queue and engine command modules.
- Add tests for extracted Electron pure helpers.
- Continue splitting large command families and renderer internals now that `src/main.py` is off the audit hotspot list.

### Week 2

- Add desktop workflow QA script or automated Electron smoke coverage.
- Add "Open last output" and "Open project folder" workflow.
- Add render cache regression coverage.
- Add first golden render fixtures.

### Week 3

- Add FFprobe duration assertions for golden fixtures.
- Harden media relink and missing asset repair flow.
- Add generator validity tests for project-producing commands.
- Continue reducing `App.tsx`, Electron IPC orchestration, and renderer internals.

### Week 4

- Run packaging builds.
- Test packaged app on a clean profile.
- Update docs command matrix and release checklist.
- Produce a release candidate report with all gates and known limitations.

## Definition Of Done For The Next Release

The next release should not ship until all of these are true:

- `python scripts\verify_local.py` passes.
- Desktop `npm run verify` passes.
- Backend smoke tests pass.
- At least one preview render and one final render are produced.
- Quality check has zero issues on the default smoke project.
- Architecture refactors preserve CLI and IPC contracts.
- Desktop core workflow is manually or automatically verified.
- Packaging either passes or is explicitly excluded from the release scope.
- README states the fastest reliable workflow first.
- Every feature described as stable has a smoke command, expected output, and verification status.
