from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


def ffmpeg_binary() -> str:
    env_binary = os.environ.get("FFMPEG_BINARY")
    if env_binary:
        return env_binary
    system_binary = shutil.which("ffmpeg")
    if system_binary:
        return system_binary
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError(
            "FFmpeg was not found. Install dependencies with: python -m pip install -r requirements.txt"
        ) from exc


def run_ffmpeg(args: list[str], *, binary: str | None = None, capture_bytes: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        [binary or ffmpeg_binary(), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not capture_bytes,
    )


def media_duration(path: Path) -> float:
    result = run_ffmpeg(["-hide_banner", "-i", str(path)])
    output = (result.stderr or "") + (result.stdout or "")
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
    if not match:
        return 0.0
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
