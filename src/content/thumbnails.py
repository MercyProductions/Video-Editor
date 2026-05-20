from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from renderer.filters import escape_text, ffmpeg_color, font_option
from utils.media import run_ffmpeg


def generate_thumbnail_set(
    source_video: Path,
    *,
    title: str,
    output_dir: Path,
    accent_color: str = "#ef4444",
    timestamps: list[float] | None = None,
) -> dict[str, Any]:
    source_video = source_video.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamps = timestamps or [0.8, 2.0, 4.0]
    outputs = []
    for aspect in ("landscape", "vertical"):
        width, height = (1280, 720) if aspect == "landscape" else (1080, 1920)
        for index, timestamp in enumerate(timestamps[:3], start=1):
            output = output_dir / f"thumbnail_{aspect}_{index}.png"
            _render_thumbnail(source_video, output, title=title, timestamp=timestamp, width=width, height=height, accent_color=accent_color)
            outputs.append({"aspect": aspect, "variant": index, "path": str(output.resolve()), "timestamp": timestamp})
    report = {"source": str(source_video), "title": title, "thumbnails": outputs}
    report_path = output_dir / "thumbnail_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    report["reportPath"] = str(report_path.resolve())
    return report


def _render_thumbnail(source: Path, output: Path, *, title: str, timestamp: float, width: int, height: int, accent_color: str) -> None:
    safe_title = escape_text(title.upper()[:64])
    accent = ffmpeg_color(accent_color)
    vf = ",".join(
        [
            f"scale={width}:{height}:force_original_aspect_ratio=increase",
            f"crop={width}:{height}",
            "eq=contrast=1.12:brightness=-0.02",
            "vignette=PI/5",
            f"drawbox=x=0:y=0:w=iw:h=ih:color={accent}@0.14:t=fill",
            f"drawbox=x=0:y=ih*0.68:w=iw:h=ih*0.32:color=black@0.62:t=fill",
            (
                "drawtext="
                f"{font_option(None)}:"
                f"text='{safe_title}':"
                f"x=(w-text_w)/2:y=h*0.72:"
                "fontsize=64:fontcolor=white:"
                "borderw=4:bordercolor=black"
            ),
            (
                "drawtext="
                f"{font_option(None)}:"
                "text='AUTO EDIT':"
                "x=w*0.06:y=h*0.08:"
                f"fontsize=34:fontcolor={accent}:"
                "borderw=2:bordercolor=black"
            ),
        ]
    )
    result = run_ffmpeg(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(max(timestamp, 0)),
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            vf,
            str(output),
        ]
    )
    if result.returncode != 0:
        fallback = (
            f"color=c=0x090806:s={width}x{height},"
            f"drawtext={font_option(None)}:text='{safe_title}':x=(w-text_w)/2:y=(h-text_h)/2:"
            "fontsize=62:fontcolor=white:borderw=4:bordercolor=black"
        )
        run_ffmpeg(["-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", fallback, "-frames:v", "1", str(output)])
