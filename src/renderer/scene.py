from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from assets.resolver import AssetResolver
from effects.graph import scene_post_filters
from effects.graphics import graphics_filters_for_layer
from effects.text import drawtext_filter, drawtext_filters_for_layer
from effects.video import media_effect_filters
from parser.models import ProjectSettings, Scene
from renderer.filters import (
    animated_position,
    ffmpeg_color,
    fmt,
    layer_window,
    position_expr,
    seconds,
)


@dataclass(slots=True)
class MediaInput:
    layer_index: int
    input_index: int
    layer_type: str
    raw: dict[str, Any]
    start: float
    duration: float
    end: float


def build_scene_render_args(
    scene: Scene,
    index: int,
    settings: ProjectSettings,
    project_root: Path,
    assets: AssetResolver,
    output: Path,
    *,
    video_encoder: str,
    encoder_preset: str,
    render_crf: int,
) -> list[str]:
    args = _base_scene_args(scene, settings)
    media_inputs = _append_media_inputs(args, scene, assets)
    args.extend(
        _scene_output_args(
            scene,
            settings,
            _scene_filter_graph(scene, index, settings, project_root, media_inputs),
            output,
            video_encoder=video_encoder,
            encoder_preset=encoder_preset,
            render_crf=render_crf,
        )
    )
    return args


def _base_scene_args(scene: Scene, settings: ProjectSettings) -> list[str]:
    return [
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


def _append_media_inputs(args: list[str], scene: Scene, assets: AssetResolver) -> list[MediaInput]:
    media_inputs: list[MediaInput] = []
    next_input = 1
    for layer_index, layer in enumerate(scene.layers):
        raw = layer.raw
        if layer.type not in {"video", "image"}:
            continue
        start, duration, end = layer_window(raw, scene.duration)
        if duration <= 0:
            continue
        asset_path = assets.resolve(str(raw["asset"]), layer.type)
        if layer.type == "image":
            _append_image_input(args, asset_path, duration)
        else:
            _append_video_input(args, asset_path, raw, duration)
        media_inputs.append(MediaInput(layer_index, next_input, layer.type, raw, start, duration, end))
        next_input += 1
    return media_inputs


def _append_image_input(args: list[str], asset_path: Path, duration: float) -> None:
    if asset_path.suffix.lower() == ".gif":
        args.extend(["-stream_loop", "-1", "-t", fmt(duration), "-i", str(asset_path)])
    else:
        args.extend(["-loop", "1", "-t", fmt(duration), "-i", str(asset_path)])


def _append_video_input(args: list[str], asset_path: Path, raw: dict[str, Any], duration: float) -> None:
    speed = float(raw.get("speed", 1) or 1)
    trim_start = float(raw.get("trimStart", 0) or 0)
    trim_end = raw.get("trimEnd")
    source_duration = (float(trim_end) - trim_start) if trim_end is not None else duration * speed
    if trim_start > 0:
        args.extend(["-ss", fmt(trim_start)])
    if source_duration > 0:
        args.extend(["-t", fmt(source_duration)])
    args.extend(["-i", str(asset_path)])


def _scene_filter_graph(
    scene: Scene,
    index: int,
    settings: ProjectSettings,
    project_root: Path,
    media_inputs: list[MediaInput],
) -> str:
    filters: list[str] = []
    current = "[0:v]"
    media_by_layer = {item.layer_index: item for item in media_inputs}
    media_counter = 0
    text_counter = 0

    for layer_index, layer in enumerate(scene.layers):
        raw = layer.raw
        if layer.type in {"video", "image"}:
            media_input = media_by_layer.get(layer_index)
            if media_input is None:
                continue
            media_counter += 1
            layer_filters, current = _media_layer_filters(
                current,
                media_input,
                scene_index=index,
                media_counter=media_counter,
                text_counter=text_counter,
            )
            filters.extend(layer_filters)
        elif layer.type == "text":
            text_counter += 1
            text_filters, current = drawtext_filters_for_layer(current, raw, scene_duration=scene.duration, label_prefix=f"s{index}_t{text_counter}")
            filters.extend(text_filters)
        elif layer.type in {"caption", "captions"}:
            text_counter += 1
            caption_filters, current = _caption_filters(current, raw, scene.duration, f"s{index}_c{text_counter}")
            filters.extend(caption_filters)
        elif layer.type in {"shape", "progress", "lower_third", "hud", "animated_background", "particle", "waveform"}:
            text_counter += 1
            graphics_filters, current = graphics_filters_for_layer(current, raw, scene_duration=scene.duration, label_prefix=f"s{index}_g{text_counter}")
            filters.extend(graphics_filters)

    current = _append_post_filters(filters, current, scene, index, project_root)
    filters.append(f"{current}format=yuv420p,fps={settings.fps}[vout]")
    return ";".join(filters)


def _media_layer_filters(
    current: str,
    media_input: MediaInput,
    *,
    scene_index: int,
    media_counter: int,
    text_counter: int,
) -> tuple[list[str], str]:
    layer_label = f"[layer_{scene_index}_{media_counter}]"
    speed = float(media_input.raw.get("speed", 1) or 1) if media_input.layer_type == "video" else 1
    media_filters = media_effect_filters(media_input.raw, media_input.duration, speed)
    media_filters[-1] = f"{media_filters[-1]}+{fmt(media_input.start)}/TB"

    output_label = f"[comp_{scene_index}_{media_counter}_{text_counter}]"
    x_expr = _overlay_position(media_input.raw, "x", media_input.start, media_input.duration)
    y_expr = _overlay_position(media_input.raw, "y", media_input.start, media_input.duration)
    return [
        f"[{media_input.input_index}:v]{','.join(media_filters)}{layer_label}",
        (
            f"{current}{layer_label}"
            f"overlay=x={x_expr}:y={y_expr}:enable='between(t,{fmt(media_input.start)},{fmt(media_input.end)})':"
            f"eof_action=pass:shortest=0{output_label}"
        ),
    ], output_label


def _overlay_position(layer: dict[str, Any], axis: str, start: float, duration: float) -> str:
    base = position_expr(layer.get(axis, 0), axis, "overlay")
    return animated_position(layer, axis, base, start=start, duration=duration, mode="overlay")


def _caption_filters(
    input_label: str,
    layer: dict[str, Any],
    scene_duration: float,
    label_prefix: str,
) -> tuple[list[str], str]:
    filters: list[str] = []
    current = input_label
    for index, item in enumerate(_caption_items(layer, scene_duration)):
        caption_layer = {**layer, **item, "type": "text"}
        start = seconds(caption_layer.get("start"), 0)
        duration = _caption_duration(caption_layer, start)
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


def _caption_items(layer: dict[str, Any], scene_duration: float) -> list[dict[str, Any]]:
    return layer.get("items") or [
        {
            "text": layer.get("text", ""),
            "start": layer.get("start", 0),
            "duration": layer.get("duration", scene_duration),
        }
    ]


def _caption_duration(caption_layer: dict[str, Any], start: float) -> float:
    if caption_layer.get("duration") is not None:
        return seconds(caption_layer.get("duration"), 0)
    if caption_layer.get("end") is not None:
        return max(seconds(caption_layer.get("end"), start) - start, 0)
    return 2


def _append_post_filters(filters: list[str], current: str, scene: Scene, index: int, project_root: Path) -> str:
    for post_index, post_filter in enumerate(scene_post_filters(scene.raw, project_root), start=1):
        output_label = f"[post_{index}_{post_index}]"
        filters.append(f"{current}{post_filter}{output_label}")
        current = output_label
    return current


def _scene_output_args(
    scene: Scene,
    settings: ProjectSettings,
    filter_graph: str,
    output: Path,
    *,
    video_encoder: str,
    encoder_preset: str,
    render_crf: int,
) -> list[str]:
    return [
        "-filter_complex",
        filter_graph,
        "-map",
        "[vout]",
        "-an",
        "-t",
        fmt(scene.duration),
        "-r",
        str(settings.fps),
        "-c:v",
        video_encoder,
        "-preset",
        encoder_preset,
        "-crf",
        str(render_crf),
        "-pix_fmt",
        "yuv420p",
        str(output),
    ]
