# Media Compatibility

The editor now uses a shared media compatibility layer for import probing, normalization, previews, and export containers. Source media is copied into the project first; normalization never modifies the original file.

## Import Formats

Video:

- `.mp4`
- `.mov`
- `.mkv`
- `.avi`
- `.webm`
- `.flv`
- `.wmv`
- `.mpeg`
- `.mpg`
- `.m4v`
- `.ts`
- `.mts`
- `.m2ts`

Common handled video codecs include H.264, H.265/HEVC, AV1, VP8, VP9, ProRes, DNxHD, MJPEG, MPEG-2, MPEG-4, and WMV3 when the local FFmpeg build can decode them.

Images:

- `.png`
- `.jpg` / `.jpeg`
- `.webp`
- `.bmp`
- `.gif`
- `.tiff` / `.tif`
- `.svg`

Transparency and alpha compositing are preserved through the renderer's RGBA layer path. Animated GIFs are treated as timed visual media during import/render instead of as a single still frame.

Audio:

- `.mp3`
- `.wav`
- `.flac`
- `.ogg`
- `.aac`
- `.m4a`

## Smart Import

Use:

```powershell
python render.py media import path\to\clip.mov path\to\music.ogg --project-dir examples/generated/import_test
```

The import pipeline detects:

- resolution
- FPS
- aspect ratio
- duration
- bitrate
- codec
- audio tracks
- HDR/SDR hints
- orientation
- VFR risk
- broken or unreadable files
- available local hardware decode APIs

It also creates, when possible:

- `assets/` copied source media
- `.ave_media/normalized/` normalized media when needed
- `.ave_media/thumbnails/`
- `.ave_media/waveforms/`
- `.ave_media/proxies/`
- `media_import_report.json`

Normalization modes:

- `auto`: transcode only when the file is VFR, has a less editing-friendly container, has an uncertain codec, or needs sample-rate/image normalization.
- `always`: transcode supported files into editing-friendly media.
- `never`: copy files and generate metadata/previews only.

## Inspect

```powershell
python render.py media inspect examples/assets/gameplay.mp4 -o output/media_inspect_gameplay.json
```

## Export Formats

The renderer selects the output container from the output extension, or from `--format`.

```powershell
python render.py render examples/project.json -o output/final_video.mov
python render.py render examples/project.json -o output/final_video.mkv
python render.py render examples/project.json -o output/final_video.webm
python render.py render examples/project.json -o output/final_video.gif
python render.py render examples/project.json -o output/frames/frame_%05d.png
python render.py render examples/project.json --format webm
```

Supported export containers:

- MP4
- MOV
- MKV
- WebM
- GIF
- image sequences

Export presets:

- YouTube
- TikTok/Reels
- Shorts
- Square
- Discord
- Instagram Reels
- High Quality Archive
- Low Size Preview
- Cinematic 4K
