from __future__ import annotations

import logging
import json
import hashlib
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from assets.resolver import AssetResolver
from media.compat import export_format_from_path
from parser.models import ProjectConfig, Scene
from renderer.audio import render_audio_mix
from renderer.ffmpeg import FFmpeg
from renderer.filters import (
    escape_expr,
    fmt,
)
from renderer.mux import mux_export
from renderer.scene import build_scene_render_args
from transitions.transitions import transition_duration, transition_type
from reports.render_report import build_render_report


def _default_output_path(project: ProjectConfig) -> Path:
    output_dir = Path.home() / "Videos" / "Automatic Video Editor" / "renders"
    project_name = _safe_stem(project.path.stem or "automatic-video")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return output_dir / f"{project_name}-final-{stamp}.mp4"


def _safe_stem(value: str) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return clean[:60] or "automatic-video"


class VideoRenderer:
    def __init__(
        self,
        project: ProjectConfig,
        *,
        output_path: Path | None = None,
        keep_temp: bool = False,
        generate_placeholders: bool = False,
        quality: str = "final",
        use_cache: bool = False,
        resume: bool = False,
        gpu: bool = False,
    ):
        self.project = project
        self.output_path = output_path or _default_output_path(project)
        self.keep_temp = keep_temp
        self.quality = quality
        self.use_cache = use_cache
        self.resume = resume
        self.gpu = gpu
        self.ffmpeg = FFmpeg()
        self.warnings: list[str] = []
        if self.gpu and not self._gpu_encoder_available():
            self.warnings.append("GPU encoder h264_nvenc was requested but is not available; using libx264.")
            self.gpu = False
        self.assets = AssetResolver(project, generate_missing=generate_placeholders)
        self.temp_dir: Path | None = None
        self.render_started_at = 0.0

    @property
    def cache_dir(self) -> Path:
        return self.output_path.parent / ".render_cache"

    @property
    def encoder_preset(self) -> str:
        return "ultrafast" if self.quality == "preview" else "veryfast"

    @property
    def render_crf(self) -> int:
        if self.quality == "preview":
            return max(self.project.settings.crf, 32)
        return self.project.settings.crf

    @property
    def video_encoder(self) -> str:
        return "h264_nvenc" if self.gpu else "libx264"

    def _gpu_encoder_available(self) -> bool:
        result = subprocess.run(
            [self.ffmpeg.binary, "-hide_banner", "-encoders"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.returncode == 0 and "h264_nvenc" in ((result.stdout or "") + (result.stderr or ""))

    def render(self) -> Path:
        self.render_started_at = time.perf_counter()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        missing_assets: list[dict[str, Any]] = []
        try:
            self.assets.verify_referenced_assets()
        except Exception as exc:
            missing_assets = [asset for asset in self.assets.asset_usage_report() if not asset["exists"]]
            self.warnings.append(str(exc))
            raise

        with tempfile.TemporaryDirectory(prefix="ave_", dir=self.output_path.parent) as temp_name:
            self.temp_dir = Path(temp_name)
            logging.info("Rendering scenes")
            scene_files = [self._render_scene(scene, index) for index, scene in enumerate(self.project.timeline)]

            logging.info("Applying transitions")
            video_path, video_duration = self._combine_scenes(scene_files)
            video_path = self._fit_video_duration(video_path, video_duration)

            logging.info("Rendering audio")
            audio_path = self._render_audio()

            logging.info("Exporting %s", export_format_from_path(self.output_path).upper())
            self._mux(video_path, audio_path, self.output_path)

            if self.keep_temp:
                keep_path = self.output_path.parent / "_last_temp"
                if keep_path.exists():
                    shutil.rmtree(keep_path)
                shutil.copytree(self.temp_dir, keep_path)
                logging.info("Kept temp files: %s", keep_path)

        build_render_report(
            self.project,
            self.output_path,
            render_time_seconds=time.perf_counter() - self.render_started_at,
            warnings=self.warnings,
            missing_assets=missing_assets,
            quality=self.quality,
            cache_enabled=self.use_cache,
            gpu_enabled=self.gpu,
        )
        return self.output_path

    def _render_scene(self, scene: Scene, index: int) -> tuple[Path, float, dict[str, Any] | None]:
        assert self.temp_dir is not None
        output = self.temp_dir / f"scene_{index:03d}_{scene.id}.mp4"
        settings = self.project.settings
        cached = self._cached_scene_path(scene, index)
        if cached and cached.exists() and (self.use_cache or self.resume):
            logging.info("Using cached scene '%s': %s", scene.id, cached)
            shutil.copy2(cached, output)
            return output, scene.duration, scene.transition_out

        args = build_scene_render_args(
            scene,
            index,
            settings,
            self.project.root_dir,
            self.assets,
            output,
            video_encoder=self.video_encoder,
            encoder_preset=self.encoder_preset,
            render_crf=self.render_crf,
        )

        logging.info("Rendering scene '%s' (%ss)", scene.id, fmt(scene.duration))
        try:
            self.ffmpeg.run(args)
        except Exception:
            if self.gpu:
                self.warnings.append("GPU encoder failed for a scene; retrying with libx264.")
                self.gpu = False
                args[args.index("h264_nvenc")] = "libx264"
                self.ffmpeg.run(args)
            else:
                raise
        if cached and self.use_cache:
            cached.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(output, cached)
        return output, scene.duration, scene.transition_out

    def _cached_scene_path(self, scene: Scene, index: int) -> Path | None:
        if not (self.use_cache or self.resume):
            return None
        cache_key = {
            "scene": scene.raw,
            "settings": {
                "width": self.project.settings.width,
                "height": self.project.settings.height,
                "fps": self.project.settings.fps,
                "crf": self.render_crf,
                "quality": self.quality,
            },
            "assets": self.project.assets,
        }
        digest = hashlib.sha256(json.dumps(cache_key, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"scene_{index:03d}_{scene.id}_{digest}.mp4"

    def _combine_scenes(self, scene_files: list[tuple[Path, float, dict[str, Any] | None]]) -> tuple[Path, float]:
        assert self.temp_dir is not None
        if len(scene_files) == 1:
            return scene_files[0][0], scene_files[0][1]

        current_path, current_duration, transition = scene_files[0]
        for index, (next_path, next_duration, next_transition) in enumerate(scene_files[1:], start=1):
            output = self.temp_dir / f"transition_{index:03d}.mp4"
            kind = transition_type(transition)
            duration = min(transition_duration(transition), current_duration, next_duration)
            if kind == "cut" or duration <= 0:
                self._concat_two(current_path, next_path, output)
                current_duration += next_duration
            else:
                self._xfade_two(
                    current_path,
                    next_path,
                    output,
                    current_duration,
                    next_duration,
                    transition or {},
                )
                current_duration += next_duration - duration
            current_path = output
            transition = next_transition
        return current_path, current_duration

    def _concat_two(self, first: Path, second: Path, output: Path) -> None:
        settings = self.project.settings
        filters = (
            f"[0:v]fps={settings.fps},settb=AVTB,setpts=PTS-STARTPTS[v0];"
            f"[1:v]fps={settings.fps},settb=AVTB,setpts=PTS-STARTPTS[v1];"
            "[v0][v1]concat=n=2:v=1:a=0,format=yuv420p[v]"
        )
        self.ffmpeg.run(
            [
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-r",
                str(settings.fps),
                "-i",
                str(first),
                "-r",
                str(settings.fps),
                "-i",
                str(second),
                "-filter_complex",
                filters,
                "-map",
                "[v]",
                "-r",
                str(settings.fps),
                "-c:v",
                self.video_encoder,
                "-preset",
                self.encoder_preset,
                "-crf",
                str(self.render_crf),
                str(output),
            ]
        )

    def _xfade_two(
        self,
        first: Path,
        second: Path,
        output: Path,
        current_duration: float,
        next_duration: float,
        transition: dict[str, Any],
    ) -> None:
        settings = self.project.settings
        duration = min(transition_duration(transition), current_duration)
        offset = max(current_duration - duration, 0)

        first_split_count = 2 if offset > 0.001 else 1
        second_has_tail = next_duration - duration > 0.001
        second_split_count = 2 if second_has_tail else 1
        first_split_labels = "".join(f"[v0s{i}]" for i in range(first_split_count))
        second_split_labels = "".join(f"[v1s{i}]" for i in range(second_split_count))
        filters: list[str] = [
            f"[0:v]fps={settings.fps},settb=AVTB,format=rgba,split={first_split_count}{first_split_labels}",
            f"[1:v]fps={settings.fps},settb=AVTB,format=rgba,split={second_split_count}{second_split_labels}",
        ]

        segments: list[str] = []
        first_transition_source = "[v0s0]"
        if offset > 0.001:
            filters.append(
                f"[v0s0]trim=start=0:end={fmt(offset)},setpts=PTS-STARTPTS,format=yuv420p[head]"
            )
            segments.append("[head]")
            first_transition_source = "[v0s1]"

        filters.append(
            f"{first_transition_source}trim=start={fmt(offset)}:end={fmt(current_duration)},"
            "setpts=PTS-STARTPTS[first_x]"
        )
        filters.append(
            f"[v1s0]trim=start=0:end={fmt(duration)},setpts=PTS-STARTPTS[second_x]"
        )
        transition_label = self._transition_segment_filter(filters, transition, duration)
        segments.append(transition_label)

        if second_has_tail:
            filters.append(
                f"[v1s1]trim=start={fmt(duration)},setpts=PTS-STARTPTS,format=yuv420p[tail]"
            )
            segments.append("[tail]")

        if len(segments) == 1:
            filters.append(f"{segments[0]}format=yuv420p[v]")
        else:
            filters.append("".join(segments) + f"concat=n={len(segments)}:v=1:a=0,format=yuv420p[v]")

        filter_graph = ";".join(filters)
        self.ffmpeg.run(
            [
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-r",
                str(settings.fps),
                "-i",
                str(first),
                "-r",
                str(settings.fps),
                "-i",
                str(second),
                "-filter_complex",
                filter_graph,
                "-map",
                "[v]",
                "-r",
                str(settings.fps),
                "-c:v",
                self.video_encoder,
                "-preset",
                self.encoder_preset,
                "-crf",
                str(self.render_crf),
                str(output),
            ]
        )

    def _transition_segment_filter(
        self,
        filters: list[str],
        transition: dict[str, Any],
        duration: float,
    ) -> str:
        kind = transition_type(transition)
        d = fmt(duration)
        if kind == "fadeToBlack":
            filters.append(f"[first_x]fade=t=out:st=0:d={d}:color=black[first_fade]")
            filters.append(f"[second_x]fade=t=in:st=0:d={d}:color=black[second_fade]")
            filters.append(
                f"[first_fade][second_fade]blend=all_expr='A*(1-T/{d})+B*(T/{d})',"
                "format=yuv420p[transition]"
            )
            return "[transition]"

        if kind == "slide":
            direction = str(transition.get("direction", "left"))
            progress = escape_expr(f"min(t/{d},1)")
            if direction == "right":
                x_expr = f"-overlay_w+overlay_w*{progress}"
                y_expr = "0"
            elif direction == "up":
                x_expr = "0"
                y_expr = f"main_h-overlay_h*{progress}"
            elif direction == "down":
                x_expr = "0"
                y_expr = f"-overlay_h+overlay_h*{progress}"
            else:
                x_expr = f"main_w-overlay_w*{progress}"
                y_expr = "0"
            filters.append(
                f"[first_x][second_x]overlay=x={x_expr}:y={y_expr}:shortest=1,format=yuv420p[transition]"
            )
            return "[transition]"

        if kind == "zoom":
            width = self.project.settings.width
            height = self.project.settings.height
            progress = escape_expr(f"min(t/{d},1)")
            filters.append(
                f"[second_x]scale=w=iw*(1.08-0.08*{progress}):"
                f"h=ih*(1.08-0.08*{progress}):eval=frame,"
                f"crop=w={width}:h={height}:x=(iw-{width})/2:y=(ih-{height})/2[second_zoom]"
            )
            filters.append(
                f"[first_x][second_zoom]blend=all_expr='A*(1-T/{d})+B*(T/{d})',"
                "format=yuv420p[transition]"
            )
            return "[transition]"

        filters.append(
            f"[first_x][second_x]blend=all_expr='A*(1-T/{d})+B*(T/{d})',"
            "format=yuv420p[transition]"
        )
        return "[transition]"

    def _fit_video_duration(self, video_path: Path, current_duration: float) -> Path:
        assert self.temp_dir is not None
        target = self.project.settings.duration
        if abs(current_duration - target) < 0.05:
            return video_path

        output = self.temp_dir / "video_fitted.mp4"
        if current_duration < target:
            pad = target - current_duration
            vf = f"tpad=stop_mode=clone:stop_duration={fmt(pad)},trim=duration={fmt(target)},setpts=PTS-STARTPTS"
        else:
            vf = f"trim=duration={fmt(target)},setpts=PTS-STARTPTS"
        self.ffmpeg.run(
            [
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(video_path),
                "-vf",
                vf,
                "-an",
                "-r",
                str(self.project.settings.fps),
                "-c:v",
                self.video_encoder,
                "-preset",
                self.encoder_preset,
                "-crf",
                str(self.render_crf),
                "-pix_fmt",
                "yuv420p",
                str(output),
            ]
        )
        return output

    def _render_audio(self) -> Path:
        assert self.temp_dir is not None
        return render_audio_mix(self.ffmpeg, self.project, self.assets, self.temp_dir)

    def _mux(self, video_path: Path, audio_path: Path, output_path: Path) -> None:
        mux_export(self.ffmpeg, video_path, audio_path, output_path, self.project.settings, self.quality)
