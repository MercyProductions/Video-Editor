from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from media.compat import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from parser.models import ProjectConfig


class AssetResolutionError(FileNotFoundError):
    pass


MEDIA_EXTENSIONS = {
    "video": sorted(VIDEO_EXTENSIONS),
    "image": sorted(IMAGE_EXTENSIONS),
    "audio": sorted(AUDIO_EXTENSIONS),
}


class AssetResolver:
    def __init__(self, project: ProjectConfig, *, generate_missing: bool = False):
        self.project = project
        self.generate_missing = generate_missing

    def resolve(self, key: str, media_type: str | None = None) -> Path:
        if key not in self.project.assets:
            if self.generate_missing and media_type:
                self.project.assets[key] = f"assets/{key}{self._default_suffix(media_type)}"
            else:
                raise KeyError(f"Asset '{key}' is not defined in the assets map.")

        raw_path = Path(self.project.assets[key])
        path = raw_path if raw_path.is_absolute() else self.project.root_dir / raw_path
        path = path.resolve()
        if path.exists() and path.is_dir():
            found = self._first_media_file(path, media_type)
            if found:
                logging.debug("Resolved asset folder '%s' -> %s", key, found)
                return found
            if self.generate_missing and media_type:
                path = path / f"{key}{self._default_suffix(media_type)}"

        if not path.exists():
            if self.generate_missing and media_type:
                self._generate_placeholder(key, path, media_type)
            else:
                expected = ", ".join(MEDIA_EXTENSIONS.get(media_type or "", [])) or "any media file"
                raise AssetResolutionError(
                    f"Asset '{key}' not found: {path}. Expected {media_type or 'media'} ({expected}). "
                    "Run with --generate-placeholders to create test assets automatically."
                )
        logging.debug("Resolved asset '%s' -> %s", key, path)
        return path

    def verify_referenced_assets(self) -> None:
        referenced = self.referenced_assets()
        logging.info("Loading assets: %d referenced", len(referenced))
        for item in referenced:
            self.resolve(str(item["asset"]), str(item["mediaType"]))

    def referenced_assets(self) -> list[dict[str, Any]]:
        referenced: dict[str, dict[str, Any]] = {}
        for scene in self.project.timeline:
            for layer in scene.layers:
                asset = layer.raw.get("asset")
                if asset:
                    key = str(asset)
                    referenced.setdefault(
                        key,
                        {
                            "asset": key,
                            "mediaType": "image" if layer.type == "image" else "video",
                            "usedBy": [],
                        },
                    )
                    referenced[key]["usedBy"].append(f"scene:{scene.id}/layer:{layer.type}")
        for track in self.project.audio:
            referenced.setdefault(
                track.asset,
                {
                    "asset": track.asset,
                    "mediaType": "audio",
                    "usedBy": [],
                },
            )
            referenced[track.asset]["usedBy"].append("audio")
        return list(referenced.values())

    def asset_usage_report(self) -> list[dict[str, Any]]:
        report: list[dict[str, Any]] = []
        for item in self.referenced_assets():
            key = str(item["asset"])
            media_type = str(item["mediaType"])
            raw = self.project.assets.get(key)
            path = None
            exists = False
            error = None
            try:
                path = self.resolve(key, media_type)
                exists = path.exists()
            except Exception as exc:  # report-only path; caller wants all missing assets at once
                error = str(exc)
                if raw:
                    candidate = Path(raw)
                    path = candidate if candidate.is_absolute() else self.project.root_dir / candidate
            report.append(
                {
                    "asset": key,
                    "mediaType": media_type,
                    "configuredPath": raw,
                    "resolvedPath": str(path.resolve()) if path else None,
                    "exists": exists,
                    "usedBy": item["usedBy"],
                    "error": error,
                }
            )
        return report

    def _first_media_file(self, folder: Path, media_type: str | None) -> Path | None:
        extensions = MEDIA_EXTENSIONS.get(media_type or "", sum(MEDIA_EXTENSIONS.values(), []))
        for extension in extensions:
            match = next(folder.glob(f"*{extension}"), None)
            if match:
                return match.resolve()
        return None

    def _default_suffix(self, media_type: str) -> str:
        if media_type == "audio":
            return ".wav"
        if media_type == "image":
            return ".png"
        return ".mp4"

    def _ffmpeg_binary(self) -> str:
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
                "Cannot generate placeholder assets because FFmpeg is unavailable. "
                "Install dependencies with: python -m pip install -r requirements.txt"
            ) from exc

    def _run_ffmpeg(self, args: list[str]) -> None:
        cmd = [self._ffmpeg_binary(), *args]
        result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    def _generate_placeholder(self, key: str, path: Path, media_type: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        width = self.project.settings.width
        height = self.project.settings.height
        fps = self.project.settings.fps
        duration = max(min(self.project.settings.duration, 8), 3)
        logging.info("Generating placeholder %s asset '%s': %s", media_type, key, path)

        if media_type == "image":
            self._run_ffmpeg(
                [
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=0x1f2937:s={width}x{height}:d=1",
                    "-vf",
                    "drawbox=x=40:y=40:w=iw-80:h=ih-80:color=0x38bdf8@0.75:t=18,format=rgba",
                    "-frames:v",
                    "1",
                    str(path),
                ]
            )
            return

        if media_type == "audio":
            self._run_ffmpeg(
                [
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    f"sine=frequency=220:sample_rate=48000:duration={duration}",
                    "-c:a",
                    "pcm_s16le",
                    str(path),
                ]
            )
            return

        self._run_ffmpeg(
            [
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"testsrc2=size={width}x{height}:rate={fps}:duration={duration}",
                "-vf",
                "format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "22",
                str(path),
            ]
        )
