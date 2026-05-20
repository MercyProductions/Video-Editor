from __future__ import annotations

from typing import Any

from renderer.filters import (
    alpha_expression,
    animated_position,
    escape_text,
    ffmpeg_color,
    fmt,
    font_option,
    layer_window,
    position_expr,
)


def drawtext_filter(
    input_label: str,
    output_label: str,
    layer: dict[str, Any],
    *,
    text: str,
    start: float,
    duration: float,
    scene_duration: float,
    enable_start: float | None = None,
    enable_end: float | None = None,
) -> str:
    end = start + duration
    enable_start = start if enable_start is None else enable_start
    enable_end = end if enable_end is None else enable_end

    x_base = position_expr(layer.get("x", "center"), "x", "text")
    y_base = position_expr(layer.get("y", "center"), "y", "text")
    x_expr = animated_position(layer, "x", x_base, start=start, duration=duration, mode="text")
    y_expr = animated_position(layer, "y", y_base, start=start, duration=duration, mode="text")

    font_size = fmt(float(layer.get("fontSize", 64)))
    options = [
        font_option(layer.get("fontFamily")),
        f"text='{escape_text(text)}'",
        f"fontsize={font_size}",
        f"fontcolor={ffmpeg_color(layer.get('color'), '#ffffff')}",
        f"x={x_expr}",
        f"y={y_expr}",
        f"enable='between(t,{fmt(enable_start)},{fmt(min(enable_end, scene_duration))})'",
    ]

    stroke_width = float(layer.get("strokeWidth", 0) or 0)
    if stroke_width > 0:
        options.append(f"borderw={fmt(stroke_width)}")
        options.append(f"bordercolor={ffmpeg_color(layer.get('strokeColor'), '#000000')}")

    if layer.get("shadowColor"):
        options.append(f"shadowcolor={ffmpeg_color(layer.get('shadowColor'), '#000000')}")
        options.append(f"shadowx={fmt(float(layer.get('shadowX', 4)))}")
        options.append(f"shadowy={fmt(float(layer.get('shadowY', 4)))}")

    if layer.get("box"):
        options.append("box=1")
        options.append(f"boxcolor={ffmpeg_color(layer.get('boxColor'), '#00000080', alpha=None)}")
        options.append(f"boxborderw={fmt(float(layer.get('boxPadding', 16)))}")

    if layer.get("lineSpacing") is not None:
        options.append(f"line_spacing={fmt(float(layer.get('lineSpacing', 0) or 0))}")

    alpha = alpha_expression(layer, start, duration)
    if alpha:
        options.append(f"alpha='{alpha}'")

    return f"{input_label}drawtext={':'.join(options)}{output_label}"


def drawtext_filters_for_layer(
    input_label: str,
    layer: dict[str, Any],
    *,
    scene_duration: float,
    label_prefix: str,
) -> tuple[list[str], str]:
    start, duration, end = layer_window(layer, scene_duration)
    if duration <= 0:
        return [], input_label

    text = str(layer.get("text", ""))
    animation = layer.get("animation")
    if isinstance(animation, dict):
        animation_name = animation.get("in")
    else:
        animation_name = animation

    if animation_name != "typewriter" or len(text) <= 1:
        output_label = f"[{label_prefix}_text]"
        return [
            drawtext_filter(
                input_label,
                output_label,
                layer,
                text=text,
                start=start,
                duration=duration,
                scene_duration=scene_duration,
            )
        ], output_label

    filters: list[str] = []
    current = input_label
    max_steps = min(len(text), 160)
    step = max(float(layer.get("typewriterDuration", duration * 0.55)) / max_steps, 0.01)
    for index in range(1, max_steps + 1):
        shown_text = text[:index]
        enable_start = start + (index - 1) * step
        enable_end = end if index == max_steps else min(start + index * step, end)
        output_label = f"[{label_prefix}_tw_{index}]"
        filters.append(
            drawtext_filter(
                current,
                output_label,
                layer,
                text=shown_text,
                start=start,
                duration=duration,
                scene_duration=scene_duration,
                enable_start=enable_start,
                enable_end=enable_end,
            )
        )
        current = output_label
    return filters, current
