from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from renderer.ffmpeg import FFmpeg  # noqa: E402


def main() -> int:
    assets = Path(__file__).resolve().parent / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    ffmpeg = FFmpeg()

    logo = assets / "logo.png"
    clip = assets / "gameplay.mp4"
    music = assets / "song.wav"
    beat_music = assets / "beat_music.wav"

    ffmpeg.run(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x101827:s=512x512:r=1:d=1",
            "-vf",
            (
                "drawbox=x=42:y=42:w=428:h=428:color=0x22c55e@0.90:t=24,"
                "drawbox=x=118:y=118:w=276:h=276:color=0x38bdf8@0.72:t=fill,"
                "drawbox=x=176:y=176:w=160:h=160:color=0xf8fafc@0.92:t=12,"
                "format=rgba"
            ),
            "-frames:v",
            "1",
            str(logo),
        ]
    )

    ffmpeg.run(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=1280x720:rate=30:duration=7",
            "-vf",
            (
                "drawbox=x='(w-240)/2+180*sin(t*1.6)':"
                "y='(h-140)/2+95*cos(t*1.2)':w=240:h=140:"
                "color=0xffffff@0.35:t=fill,"
                "drawbox=x='(w-360)/2':y='h-130':w=360:h=56:"
                "color=0x020617@0.70:t=fill,"
                "format=yuv420p"
            ),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            str(clip),
        ]
    )

    ffmpeg.run(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:sample_rate=48000:duration=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=330:sample_rate=48000:duration=10",
            "-filter_complex",
            (
                "[0:a]volume=0.28[a0];"
                "[1:a]volume=0.16[a1];"
                "[a0][a1]amix=inputs=2:duration=longest,"
                "afade=t=in:st=0:d=0.4,afade=t=out:st=9:d=1[a]"
            ),
            "-map",
            "[a]",
            "-c:a",
            "pcm_s16le",
            str(music),
        ]
    )

    ffmpeg.run(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            (
                "aevalsrc=0.12*sin(2*PI*220*t)+"
                "if(lt(mod(t\\,0.5)\\,0.08)\\,0.8*sin(2*PI*70*t)\\,0):"
                "s=48000:d=12"
            ),
            "-c:a",
            "pcm_s16le",
            str(beat_music),
        ]
    )

    print(f"Created sample assets in {assets}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
