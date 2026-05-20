# YouTube Shorts Auto-Creation Mode

YouTube Shorts mode turns a local prompt into a vertical short-form project JSON and, when requested, a rendered MP4. It stays local-first and uses the JSON renderer as the source of truth.

## Command

```powershell
python render.py youtube-short "Create a YouTube Short for my automatic troubleshooter. It scans missing runtimes, launch blockers, anti-cheat conflicts, and Windows security settings. Make it premium red/black, cinematic, and under 45 seconds." --assets examples/assets --music examples/assets/beat_music.wav --logo examples/assets/logo.png -o examples/generated/youtube_short_auto --render --quality preview --cache
```

## Outputs

The output folder contains:

- `project.json`: renderable 1080x1920 Shorts project.
- `short_plan.json`: concept, hook, script, scene list, title cards, captions, timing, style, and music-sync metadata.
- `review_summary.txt`: readable generation summary for approval.
- `preview/timeline_summary.json`: timeline preview report.
- `preview/render_plan.txt`: render plan.
- `final_video.mp4`: rendered video when `--render` is used.
- `youtube_short_summary.json`: machine-readable command summary.

## Structure

For a normal 45-second Short the generator uses:

- Hook: 0-3 seconds.
- Problem: 3-10 seconds.
- Feature showcase: 10-30 seconds.
- Result/payoff: 30-40 seconds.
- CTA/outro: 40-45 seconds.

Shorter durations are scaled proportionally while preserving the same hook/problem/body/result/CTA shape.

## Options

- `--assets`: optional folder of local clips. The mode selects highlight segments when possible.
- `--music`: optional local music file. The mode analyzes beats/bass drops and stores music-sync metadata.
- `--logo`: optional logo image for intro/outro title cards.
- `--style`: `auto` or any style preset such as `red_black_aegis`, `clean_cinematic`, or `minimal_tech`.
- `--duration`: target duration, clamped to 8-45 seconds.
- `--render`: render `final_video.mp4`.
- `--quality`: `preview` or `final`.
- `--cache`: reuse scene render cache.
- `--gpu`: try GPU H.264 encoding if available.

## Notes

The generator is deterministic and local-rule-based for now. It does not require cloud calls or API keys. The generated JSON can be opened in Advanced Mode and edited like any other project.

