# Advanced Cinematic Systems

The advanced systems pass upgrades normal project JSON with deterministic, renderable intelligence. It keeps JSON as the source of truth and does not require cloud services.

## Commands

Apply advanced systems to any project JSON:

```powershell
python render.py advanced examples/project.json -o examples/generated/project.advanced_systems.json --report output/project_advanced_systems_report.json
```

Create a raw desktop showcase with advanced systems enabled:

```powershell
python render.py showcase examples/assets/gameplay.mp4 --music examples/assets/beat_music.wav --logo examples/assets/logo.png --overrides examples/showcase_overrides.json --advanced-output output/advanced_systems_report.json -o examples/generated/advanced_systems_showcase_project.json --render --render-output output/advanced_systems_showcase_preview.mp4 --quality preview --cache
```

## Implemented Systems

- Color management: Rec.709 SDR export tags, SDR/HDR detection, gamma/color nodes, tone-map planning, LUT stack support, export validation metadata.
- Advanced motion analysis: frame-difference flow vectors, focus tracks, stabilized predictive pan/zoom, keyframed camera metadata rendered by FFmpeg.
- Semantic scene understanding: detects showcase workflow moments such as login, dashboard, scan, success, analytics, setup, interaction highlight, and payoff.
- Temporal editing memory: tracks transitions, zoom frequency, lighting intensity, pacing rhythm, and prevents repeated transition/zoom behavior.
- Professional typography: safe-zone clamping, multiline balancing, font fallback metadata, line spacing, caption readability timing, stroke/box defaults.
- Audio intelligence: compressor, limiter, ducking, bass emphasis, auto-balance, and loudness normalization settings for the existing FFmpeg audio chain.
- Render graph architecture: scene/layer/effect dependency graph, stable cache keys, partial scene rerender metadata.
- GPU/VRAM management: working-set estimate, hardware encoder detection, backend fallback plan, preview quality guidance.
- Intelligent asset scoring: local asset quality ranking, duplicate detection by hash, motion/readability/highlight assessment.
- Human override system: locked scenes, locked transitions, AI-disabled scenes, protected regions, forced timing, revert-by-section metadata.
- Deterministic rendering: fixed project fingerprint, stable effect node IDs, deterministic node order, stable cache invalidation.
- Asset license/safety: local attribution metadata, unknown music/font warnings, safe export mode metadata.
- Hardware capture awareness: HDR, ultrawide, likely VFR, DPI scaling, OBS/compression artifact risk, multi-monitor inference.
- AI explainability: scene-level confidence, edit reasons, "why this cut happened", and safe AI boundaries.
- Creative direction: energy curves, tension/reveal/payoff phases, visual crescendo, pacing structure.

## Output Files

The advanced report contains:

- `systems`: all advanced-system outputs
- `decisions`: scene-level edits made by the engine
- `warnings`: export, license, capture, and safety warnings
- `project`: the upgraded renderable JSON
- `projectFingerprint`: deterministic fingerprint for reproducibility

