from __future__ import annotations

from typing import Any

from effects.text import drawtext_filter
from renderer.filters import ffmpeg_color, fmt, layer_window


def graphics_filters_for_layer(
    input_label: str,
    layer: dict[str, Any],
    *,
    scene_duration: float,
    label_prefix: str,
) -> tuple[list[str], str]:
    kind = str(layer.get("type", "")).lower()
    if kind == "shape":
        return _shape_filter(input_label, layer, scene_duration, label_prefix)
    if kind == "progress":
        return _progress_filters(input_label, layer, scene_duration, label_prefix)
    if kind in {"lower_third", "hud"}:
        return _lower_third_filters(input_label, layer, scene_duration, label_prefix, hud=kind == "hud")
    if kind == "animated_background":
        return _animated_background_filters(input_label, layer, scene_duration, label_prefix)
    if kind == "particle":
        return _particle_filters(input_label, layer, scene_duration, label_prefix)
    if kind == "waveform":
        return _waveform_filters(input_label, layer, scene_duration, label_prefix)
    return [], input_label


def _shape_filter(input_label: str, layer: dict[str, Any], scene_duration: float, label_prefix: str) -> tuple[list[str], str]:
    start, duration, end = layer_window(layer, scene_duration)
    w = layer.get("width", "iw")
    h = layer.get("height", "ih")
    x = _box_position_expr(layer.get("x", 0), "x", w)
    y = _box_position_expr(layer.get("y", 0), "y", h)
    color = ffmpeg_color(layer.get("color"), "#ffffff", alpha=float(layer.get("opacity", 1) or 1))
    output = f"[{label_prefix}_shape]"
    return [
        f"{input_label}drawbox=x={x}:y={y}:w={w}:h={h}:color={color}:t=fill:enable='between(t,{fmt(start)},{fmt(end)})'{output}"
    ], output


def _progress_filters(input_label: str, layer: dict[str, Any], scene_duration: float, label_prefix: str) -> tuple[list[str], str]:
    start, duration, end = layer_window(layer, scene_duration)
    x = layer.get("x", "10%")
    y = layer.get("y", "90%")
    width = float(layer.get("width", 720) or 720)
    height = float(layer.get("height", 14) or 14)
    x_expr = _box_position_expr(x, "x", width)
    y_expr = _box_position_expr(y, "y", height)
    progress = f"min(max((t-{fmt(start)})/{fmt(max(duration, 0.01))},0),1)"
    bg = f"[{label_prefix}_progress_bg]"
    fg = f"[{label_prefix}_progress_fg]"
    filters = [
        f"{input_label}drawbox=x={x_expr}:y={y_expr}:w={fmt(width)}:h={fmt(height)}:color={ffmpeg_color(layer.get('backgroundColor'), '#000000', alpha=0.45)}:t=fill:enable='between(t,{fmt(start)},{fmt(end)})'{bg}",
        f"{bg}drawbox=x={x_expr}:y={y_expr}:w='{fmt(width)}*{progress}':h={fmt(height)}:color={ffmpeg_color(layer.get('color'), '#ef4444', alpha=float(layer.get('opacity', 1) or 1))}:t=fill:enable='between(t,{fmt(start)},{fmt(end)})'{fg}",
    ]
    return filters, fg


def _lower_third_filters(
    input_label: str,
    layer: dict[str, Any],
    scene_duration: float,
    label_prefix: str,
    *,
    hud: bool,
) -> tuple[list[str], str]:
    start, duration, end = layer_window(layer, scene_duration)
    x = float(layer.get("x", 88) if isinstance(layer.get("x", 88), (int, float)) else 88)
    y = float(layer.get("y", 770 if not hud else 72) if isinstance(layer.get("y", 770 if not hud else 72), (int, float)) else (72 if hud else 770))
    width = float(layer.get("width", 880 if not hud else 520) or 880)
    height = float(layer.get("height", 132 if not hud else 76) or 132)
    box = f"[{label_prefix}_box]"
    color = layer.get("boxColor", "#000000aa" if not hud else "#05070dcc")
    filters = [
        f"{input_label}drawbox=x={fmt(x)}:y={fmt(y)}:w={fmt(width)}:h={fmt(height)}:color={ffmpeg_color(color)}:t=fill:enable='between(t,{fmt(start)},{fmt(end)})'{box}"
    ]
    title_layer = {
        **layer,
        "x": x + 24,
        "y": y + (16 if hud else 20),
        "fontSize": layer.get("fontSize", 42 if hud else 54),
        "color": layer.get("color", "#ffffff"),
        "strokeWidth": layer.get("strokeWidth", 0),
    }
    title_out = f"[{label_prefix}_title]"
    filters.append(drawtext_filter(box, title_out, title_layer, text=str(layer.get("title", layer.get("text", "TITLE"))), start=start, duration=duration, scene_duration=scene_duration))
    subtitle = layer.get("subtitle")
    if subtitle:
        subtitle_layer = {**title_layer, "y": y + (50 if hud else 82), "fontSize": layer.get("subtitleSize", 28 if hud else 34), "color": layer.get("subtitleColor", "#cbd5e1")}
        subtitle_out = f"[{label_prefix}_subtitle]"
        filters.append(drawtext_filter(title_out, subtitle_out, subtitle_layer, text=str(subtitle), start=start, duration=duration, scene_duration=scene_duration))
        return filters, subtitle_out
    return filters, title_out


def _animated_background_filters(input_label: str, layer: dict[str, Any], scene_duration: float, label_prefix: str) -> tuple[list[str], str]:
    start, duration, end = layer_window(layer, scene_duration)
    color = ffmpeg_color(layer.get("color"), "#ef4444", alpha=float(layer.get("opacity", 0.12) or 0.12))
    output = f"[{label_prefix}_animated_bg]"
    speed = float(layer.get("speed", 80) or 80)
    filters = [
        f"{input_label}drawbox=x='mod(t*{fmt(speed)},iw)-iw':y=0:w=iw:h=ih:color={color}:t=fill:enable='between(t,{fmt(start)},{fmt(end)})'{output}"
    ]
    return filters, output


def _particle_filters(input_label: str, layer: dict[str, Any], scene_duration: float, label_prefix: str) -> tuple[list[str], str]:
    start, duration, end = layer_window(layer, scene_duration)
    count = int(layer.get("count", 18) or 18)
    color = ffmpeg_color(layer.get("color"), "#ffffff", alpha=float(layer.get("opacity", 0.4) or 0.4))
    current = input_label
    filters: list[str] = []
    for index in range(max(1, min(count, 48))):
        x = f"mod({index * 97}+t*{20 + index % 7 * 8},iw)"
        y = f"mod({index * 53}+t*{14 + index % 5 * 5},ih)"
        output = f"[{label_prefix}_p{index}]"
        size = 2 + index % 4
        filters.append(f"{current}drawbox=x='{x}':y='{y}':w={size}:h={size}:color={color}:t=fill:enable='between(t,{fmt(start)},{fmt(end)})'{output}")
        current = output
    return filters, current


def _box_position_expr(value: Any, axis: str, size: Any) -> str:
    main = "iw" if axis == "x" else "ih"
    size_expr = fmt(float(size)) if isinstance(size, (int, float)) else str(size)
    if value is None:
        value = 0
    if isinstance(value, (int, float)):
        return fmt(float(value))
    raw = str(value).strip()
    lower = raw.lower()
    if lower in {"center", "middle"}:
        return f"({main}-{size_expr})/2"
    if axis == "x":
        if lower == "left":
            return "0"
        if lower == "right":
            return f"{main}-{size_expr}"
    if axis == "y":
        if lower == "top":
            return "0"
        if lower == "bottom":
            return f"{main}-{size_expr}"
    if raw.endswith("%"):
        return f"{main}*{fmt(float(raw[:-1]) / 100)}"
    return raw


def _waveform_filters(input_label: str, layer: dict[str, Any], scene_duration: float, label_prefix: str) -> tuple[list[str], str]:
    start, duration, end = layer_window(layer, scene_duration)
    bars = int(layer.get("bars", 28) or 28)
    x0 = float(layer.get("x", 80) if isinstance(layer.get("x", 80), (int, float)) else 80)
    y0 = float(layer.get("y", 920) if isinstance(layer.get("y", 920), (int, float)) else 920)
    bar_w = float(layer.get("barWidth", 8) or 8)
    gap = float(layer.get("gap", 6) or 6)
    max_h = float(layer.get("height", 90) or 90)
    color = ffmpeg_color(layer.get("color"), "#6db5a5", alpha=float(layer.get("opacity", 0.75) or 0.75))
    current = input_label
    filters: list[str] = []
    for index in range(max(4, min(bars, 64))):
        height = f"{fmt(max_h * 0.25)}+{fmt(max_h * 0.75)}*abs(sin(t*{fmt(2.2 + index * 0.07)}+{fmt(index * 0.4)}))"
        x = x0 + index * (bar_w + gap)
        output = f"[{label_prefix}_wave{index}]"
        filters.append(f"{current}drawbox=x={fmt(x)}:y='{fmt(y0)}-({height})':w={fmt(bar_w)}:h='{height}':color={color}:t=fill:enable='between(t,{fmt(start)},{fmt(end)})'{output}")
        current = output
    return filters, current
