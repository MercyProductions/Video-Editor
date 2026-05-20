# Troubleshooting

Start with the local hardening checks:

```powershell
python render.py dependency-check
python render.py diagnostics run examples/project.json
python render.py performance-report
python render.py privacy-report
```

Common fixes:

- Missing FFmpeg: install FFmpeg, set `FFMPEG_BINARY`, or install `imageio-ffmpeg`.
- Missing assets: run `python render.py preview project.json` and relink paths.
- Failed render: retry with `python render.py reliable-render project.json --attempts 2 --cache --resume`.
- Corrupted project: run `python render.py recovery recover-corrupt project.json -o recovered.json`.
- Slow previews: use preview quality, cache, and proxy workflows before final export.
