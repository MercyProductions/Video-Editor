# Foundation Systems

The foundation pass applies stability and workflow guarantees to an existing project JSON while keeping source media untouched. It is local-first, deterministic, and still renders through the normal FFmpeg pipeline.

## Command

```powershell
python render.py foundation-pass examples/generated/mvp_0_1_quick_create.json -o examples/generated/mvp_0_1_quick_create.foundation.json --report output/foundation_report.json --generate-proxies --benchmark
```

Render the normalized project:

```powershell
python render.py render examples/generated/mvp_0_1_quick_create.foundation.json -o output/foundation_mvp_render.mp4 --quality preview --cache
```

## What It Does

- Frame-accurate timeline: rounds scene, layer, caption, transition, and audio timings to the project FPS timebase and stores SMPTE-style frame metadata.
- Non-destructive editing: records immutable source references, hashes, and render-time edit operations without changing source media.
- Undo/redo history: writes before/after snapshots and metadata diffs into `.ave_metadata/history`.
- Proxy media: optionally generates low-resolution proxy MP4s for video assets.
- Background tasks: writes prioritized local task files for thumbnail, waveform, proxy, analysis, indexing, and render work.
- Keyframes: normalizes camera/keyframe metadata for timeline-bound animation tracks.
- GPU/effect pipeline: builds effect pass cache manifests for existing FFmpeg effect graphs and GPU-ready fallback planning.
- AI model lifecycle: records local model health, task routing, lazy-loading/fallback policy, and no-key local operation.
- Structured metadata: writes versioned project intelligence into `.ave_metadata/project.meta.json`.
- Hardware abstraction: detects local hardware encoder availability and software fallback.
- Integrity/recovery: writes transaction journals and checks project integrity.
- Accessibility/safety: scores caption speed, safe zones, pacing, and flashing risk.
- Performance/benchmarking: records pass timings, memory snapshot, cache size, and stress estimates.
- Multi-layer cache: creates tracked cache buckets for thumbnails, proxies, shaders, waveforms, AI analysis, previews, and timeline previews.
- Creative taste model: derives pacing, transition philosophy, caption density, and editing personality.

## Output

The foundation report includes one `systems` object with all 15 foundation areas, plus validation status and timing diagnostics. The normalized project remains normal project JSON and can be rendered with `python render.py render`.

