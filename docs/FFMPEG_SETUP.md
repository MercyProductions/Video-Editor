# FFmpeg Setup

The engine renders through FFmpeg. It checks this order:

1. `FFMPEG_BINARY`
2. `ffmpeg` on `PATH`
3. `imageio-ffmpeg` from Python dependencies

Check your setup:

```powershell
python render.py dependency-check -o output/dependency_report.json
```

GPU encoding is optional. If no NVIDIA, Intel, or AMD hardware encoder is found, CPU rendering remains supported.
