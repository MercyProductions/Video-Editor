from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path


class FFmpeg:
    def __init__(self, binary: str | None = None):
        self.binary = binary or self._locate_binary()
        logging.info("Using FFmpeg: %s", self.binary)

    def _locate_binary(self) -> str:
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
                "FFmpeg was not found on PATH and imageio-ffmpeg is not installed. "
                "Install dependencies with: python -m pip install -r requirements.txt"
            ) from exc

    def run(self, args: list[str], *, cwd: Path | None = None) -> None:
        cmd = [self.binary, *args]
        logging.debug("FFmpeg command: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}:\n{message}")
