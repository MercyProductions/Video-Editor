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
from effects.graph import scene_post_filters
from effects.graphics import graphics_filters_for_layer
from effects.text import drawtext_filter, drawtext_filters_for_layer
from effects.video import media_effect_filters
from media.compat import export_format_from_path
from parser.models import ProjectConfig, Scene
from renderer.ffmpeg import FFmpeg
from renderer.filters import (
    animated_position,
    escape_expr,
    ffmpeg_color,
    fmt,
    layer_window,
    position_expr,
    seconds,
)
from transitions.transitions import transition_duration, transition_type
from reports.render_report import build_render_report


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
        app_root = Path(__file__).resolve().parents[2]
        self.output_path = output_path or (app_root / "output" / "final_video.mp4")
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

        args = [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            (
                f"color=c={ffmpeg_color(settings.background)}:"
                f"s={settings.width}x{settings.height}:"
                f"r={settings.fps}:d={fmt(scene.duration)}"
            ),
        ]

        media_inputs: list[tuple[int, dict[str, Any], float, float, float]] = []
        next_input = 1
        for layer in scene.layers:
            raw = layer.raw
            if layer.type not in {"video", "image"}:
                continue
            start, duration, end = layer_window(raw, scene.duration)
            if duration <= 0:
                continue
            asset_path = self.assets.resolve(str(raw["asset"]), layer.type)
            if layer.type == "image":
                if asset_path.suffix.lower() == ".gif":
                    args.extend(["-stream_loop", "-1", "-t", fmt(duration), "-i", str(asset_path)])
                else:
                    args.extend(["-loop", "1", "-t", fmt(duration), "-i", str(asset_path)])
            else:
                speed = float(raw.get("speed", 1) or 1)
                trim_start = float(raw.get("trimStart", 0) or 0)
                trim_end = raw.get("trimEnd")
                source_duration = (float(trim_end) - trim_start) if trim_end is not None else duration * speed
                if trim_start > 0:
                    args.extend(["-ss", fmt(trim_start)])
                if source_duration > 0:
                    args.extend(["-t", fmt(source_duration)])
                args.extend(["-i", str(asset_path)])
            media_inputs.append((next_input, raw, start, duration, end))
            next_input += 1

        filters: list[str] = []
        current = "[0:v]"
        media_counter = 0
        text_counter = 0

        for layer in scene.layers:
            raw = layer.raw
            if layer.type in {"video", "image"}:
                input_index, layer_raw, start, duration, end = media_inputs[media_counter]
                media_counter += 1
                layer_label = f"[layer_{index}_{media_counter}]"
                speed = float(layer_raw.get("speed", 1) or 1) if layer.type == "video" else 1
                media_filters = media_effect_filters(layer_raw, duration, speed)
                media_filters[-1] = f"{media_filters[-1]}+{fmt(start)}/TB"
                filters.append(f"[{input_index}:v]{','.join(media_filters)}{layer_label}")

                x_base = position_expr(layer_raw.get("x", 0), "x", "overlay")
                y_base = position_expr(layer_raw.get("y", 0), "y", "overlay")
                x_expr = animated_position(
                    layer_raw,
                    "x",
                    x_base,
                    start=start,
                    duration=duration,
                    mode="overlay",
                )
                y_expr = animated_position(
                    layer_raw,
                    "y",
                    y_base,
                    start=start,
                    duration=duration,
                    mode="overlay",
                )
                output_label = f"[comp_{index}_{media_counter}_{text_counter}]"
                filters.append(
                    f"{current}{layer_label}"
                    f"overlay=x={x_expr}:y={y_expr}:enable='between(t,{fmt(start)},{fmt(end)})':"
                    f"eof_action=pass:shortest=0{output_label}"
                )
                current = output_label
            elif layer.type == "text":
                text_counter += 1
                text_filters, current = drawtext_filters_for_layer(
                    current,
                    raw,
                    scene_duration=scene.duration,
                    label_prefix=f"s{index}_t{text_counter}",
                )
                filters.extend(text_filters)
            elif layer.type in {"caption", "captions"}:
                text_counter += 1
                filters_for_caption, current = self._caption_filters(
                    current,
                    raw,
                    scene.duration,
                    f"s{index}_c{text_counter}",
                )
                filters.extend(filters_for_caption)
            elif layer.type in {"shape", "progress", "lower_third", "hud", "animated_background", "particle", "waveform"}:
                text_counter += 1
                graphics_filters, current = graphics_filters_for_layer(
                    current,
                    raw,
                    scene_duration=scene.duration,
                    label_prefix=f"s{index}_g{text_counter}",
                )
                filters.extend(graphics_filters)

        for post_index, post_filter in enumerate(scene_post_filters(scene.raw, self.project.root_dir), start=1):
            output_label = f"[post_{index}_{post_index}]"
            filters.append(f"{current}{post_filter}{output_label}")
            current = output_label
        filters.append(f"{current}format=yuv420p,fps={settings.fps}[vout]")
        args.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[vout]",
                "-an",
                "-t",
                fmt(scene.duration),
                "-r",
                str(settings.fps),
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

    def _caption_filters(
        self,
        input_label: str,
        layer: dict[str, Any],
        scene_duration: float,
        label_prefix: str,
    ) -> tuple[list[str], str]:
        caption_items = layer.get("items")
        if not caption_items:
            caption_items = [
                {
                    "text": layer.get("text", ""),
                    "start": layer.get("start", 0),
                    "duration": layer.get("duration", scene_duration),
                }
            ]

        filters: list[str] = []
        current = input_label
        for index, item in enumerate(caption_items):
            caption_layer = {**layer, **item, "type": "text"}
            start = seconds(caption_layer.get("start"), 0)
            if caption_layer.get("duration") is not None:
                duration = seconds(caption_layer.get("duration"), 0)
            elif caption_layer.get("end") is not None:
                duration = max(seconds(caption_layer.get("end"), start) - start, 0)
            else:
                duration = 2
            output = f"[{label_prefix}_{index}]"
            filters.append(
                drawtext_filter(
                    current,
                    output,
                    caption_layer,
                    text=str(caption_layer.get("text", "")),
                    start=start,
                    duration=duration,
                    scene_duration=scene_duration,
                )
            )
            current = output
        return filters, current

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
        output = self.temp_dir / "audio.m4a"
        duration = self.project.settings.duration
        if not self.project.audio:
            self.ffmpeg.run(
                [
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-t",
                    fmt(duration),
                    "-c:a",
                    "aac",
                    str(output),
                ]
            )
            return output

        args = ["-y", "-hide_banner", "-loglevel", "error"]
        for track in self.project.audio:
            raw = track.raw
            if raw.get("loop"):
                args.extend(["-stream_loop", "-1"])
            args.extend(["-i", str(self.assets.resolve(track.asset, "audio"))])

        filters: list[str] = []
        labels: list[str] = []
        for index, track in enumerate(self.project.audio):
            raw = track.raw
            start = float(raw.get("start", 0) or 0)
            trim_start = float(raw.get("trimStart", 0) or 0)
            trim_end = raw.get("trimEnd")
            requested_duration = raw.get("duration")
            if requested_duration is not None:
                track_duration = float(requested_duration)
            elif trim_end is not None:
                track_duration = max(float(trim_end) - trim_start, 0)
            else:
                track_duration = max(duration - start, 0)

            parts = [f"[{index}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"]
            if trim_start or trim_end is not None:
                trim = f"atrim=start={fmt(trim_start)}"
                if trim_end is not None:
                    trim += f":end={fmt(float(trim_end))}"
                parts.append(trim)
            parts.append(f"apad=whole_dur={fmt(track_duration)}")
            parts.append(f"atrim=duration={fmt(track_duration)}")
            parts.append("asetpts=PTS-STARTPTS")
            parts.append(f"volume={fmt(float(raw.get('volume', 1) or 1))}")
            if raw.get("voiceIsolation"):
                parts.extend(["highpass=f=90", "lowpass=f=9000"])
            if raw.get("noiseReduction"):
                parts.append("afftdn")
            bass_emphasis = raw.get("bassEmphasis")
            if bass_emphasis:
                gain = 5 if bass_emphasis is True else float(bass_emphasis)
                parts.append(f"bass=g={fmt(gain)}")
            if raw.get("ducking"):
                parts.append("acompressor=threshold=-22dB:ratio=2.5:attack=15:release=280")
            if raw.get("compressor") or raw.get("autoBalance"):
                parts.append("acompressor=threshold=-18dB:ratio=3:attack=20:release=250")
            if raw.get("limiter") or raw.get("normalize"):
                parts.append("alimiter=limit=0.95")
            if raw.get("loudnessNormalize"):
                parts.append("loudnorm=I=-16:TP=-1.5:LRA=11")
            fade_in = float(raw.get("fadeIn", 0) or 0)
            fade_out = float(raw.get("fadeOut", 0) or 0)
            if fade_in > 0:
                parts.append(f"afade=t=in:st=0:d={fmt(fade_in)}")
            if fade_out > 0 and track_duration > fade_out:
                parts.append(f"afade=t=out:st={fmt(track_duration - fade_out)}:d={fmt(fade_out)}")
            if start > 0:
                delay_ms = int(start * 1000)
                parts.append(f"adelay={delay_ms}|{delay_ms}")
            label = f"[a{index}]"
            filters.append(",".join(parts) + label)
            labels.append(label)

        filters.append(
            "".join(labels)
            + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0,"
            + f"atrim=duration={fmt(duration)},aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[aout]"
        )
        args.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[aout]",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output),
            ]
        )
        self.ffmpeg.run(args)
        return output

    def _mux(self, video_path: Path, audio_path: Path, output_path: Path) -> None:
        export_format = export_format_from_path(output_path)
        if export_format == "gif":
            fps = min(self.project.settings.fps, 15)
            width = min(self.project.settings.width, 1080)
            self.ffmpeg.run(
                [
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(video_path),
                    "-vf",
                    f"fps={fps},scale={width}:-2:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                    "-loop",
                    "0",
                    str(output_path),
                ]
            )
            return

        if export_format == "image_sequence":
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.ffmpeg.run(
                [
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(video_path),
                    "-vsync",
                    "0",
                    str(output_path),
                ]
            )
            return

        if export_format == "webm":
            self.ffmpeg.run(
                [
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(video_path),
                    "-i",
                    str(audio_path),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "libvpx-vp9",
                    "-crf",
                    "32" if self.quality == "preview" else "24",
                    "-b:v",
                    "0",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "libopus",
                    "-b:a",
                    "160k",
                    "-shortest",
                    str(output_path),
                ]
            )
            return

        container_args: list[str] = []
        if export_format in {"mp4", "mov"}:
            container_args = ["-movflags", "+faststart"]
        self.ffmpeg.run(
            [
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-colorspace",
                "bt709",
                "-color_primaries",
                "bt709",
                "-color_trc",
                "bt709",
                "-c:a",
                "aac",
                "-shortest",
                *container_args,
                str(output_path),
            ]
        )
