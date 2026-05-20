from __future__ import annotations

import math
from typing import Any

from renderer.filters import animation_config, effect_names, escape_expr, ffmpeg_color, fmt, seconds


def media_effect_filters(layer: dict[str, Any], layer_duration: float, speed: float) -> list[str]:
    filters: list[str] = ["format=rgba"]

    crop = layer.get("crop")
    if isinstance(crop, dict):
        filters.append(
            "crop="
            f"w={fmt(float(crop['width']))}:"
            f"h={fmt(float(crop['height']))}:"
            f"x={fmt(float(crop.get('x', 0)))}:"
            f"y={fmt(float(crop.get('y', 0)))}"
        )

    if layer.get("width") and layer.get("height"):
        width_value = float(layer["width"])
        height_value = float(layer["height"])
        width = fmt(width_value)
        height = fmt(height_value)
        fit = str(layer.get("fit", layer.get("objectFit", "stretch"))).lower()
        if fit == "cover":
            filters.append(f"scale=w={width}:h={height}:force_original_aspect_ratio=increase")
            filters.append(f"crop=w={width}:h={height}:x=(iw-{width})/2:y=(ih-{height})/2")
        elif fit == "contain":
            pad_color = ffmpeg_color(layer.get("padColor"), "#000000")
            pad_width = fmt(_even(width_value))
            pad_height = fmt(_even(height_value))
            filters.append(f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease")
            filters.append(f"pad=w={pad_width}:h={pad_height}:x=(ow-iw)/2:y=(oh-ih)/2:color={pad_color}")
        else:
            filters.append(f"scale=w={width}:h={height}")
    elif layer.get("width"):
        filters.append(f"scale=w={fmt(float(layer['width']))}:h=-1")
    elif layer.get("height"):
        filters.append(f"scale=w=-1:h={fmt(float(layer['height']))}")
    elif layer.get("scale"):
        scale = fmt(float(layer["scale"]))
        filters.append(f"scale=w=iw*{scale}:h=ih*{scale}:eval=frame")

    camera_filters = _camera_filters(layer)
    filters.extend(camera_filters)

    blur = float(layer.get("blur", 0) or 0)
    if blur > 0:
        filters.append(f"boxblur={fmt(blur)}")

    brightness = layer.get("brightness")
    contrast = layer.get("contrast")
    if brightness is not None or contrast is not None:
        filters.append(
            f"eq=brightness={fmt(float(brightness or 0))}:contrast={fmt(float(contrast or 1))}"
        )

    names = effect_names(layer)
    animation = animation_config(layer)
    anim_d = seconds(animation.get("duration"), 0.6)
    if animation.get("in") == "zoomIn" and anim_d > 0:
        progress = escape_expr(f"min(t/{fmt(anim_d)},1)")
        filters.append(
            f"scale=w=iw*(0.85+0.15*{progress}):h=ih*(0.85+0.15*{progress}):eval=frame"
        )
    elif animation.get("in") == "zoomOut" and anim_d > 0:
        progress = escape_expr(f"min(t/{fmt(anim_d)},1)")
        filters.append(
            f"scale=w=iw*(1.15-0.15*{progress}):h=ih*(1.15-0.15*{progress}):eval=frame"
        )

    if "pulse" in names:
        filters.append(
            "scale=w=iw*(1+0.035*sin(t*10)):h=ih*(1+0.035*sin(t*10)):eval=frame"
        )

    opacity = layer.get("opacity")
    if opacity is not None:
        filters.append(f"colorchannelmixer=aa={fmt(float(opacity))}")

    if animation.get("in") == "fade" and anim_d > 0:
        filters.append(f"fade=t=in:st=0:d={fmt(anim_d)}:alpha=1")
    if animation.get("out") == "fade" and anim_d > 0 and layer_duration > anim_d:
        filters.append(
            f"fade=t=out:st={fmt(max(layer_duration - anim_d, 0))}:d={fmt(anim_d)}:alpha=1"
        )

    filters.append(f"setpts=(PTS-STARTPTS)/{fmt(speed)}")
    return filters


def _even(value: float) -> float:
    return float(max(2, int(math.ceil(value / 2) * 2)))


def _camera_filters(layer: dict[str, Any]) -> list[str]:
    camera = layer.get("camera")
    if not isinstance(camera, dict):
        return []
    target_w = layer.get("width")
    target_h = layer.get("height")
    if not target_w or not target_h:
        return []

    mode = str(camera.get("mode", camera.get("type", "cinematic_sway")))
    intensity = max(float(camera.get("intensity", 0.35) or 0.35), 0)
    zoom = float(camera.get("zoom", 1.04 + intensity * 0.1) or 1.04)
    pan_x = float(camera.get("panX", 0) or 0)
    pan_y = float(camera.get("panY", 0) or 0)
    move_duration = max(float(camera.get("duration", 3) or 3), 0.1)
    w = fmt(float(target_w))
    h = fmt(float(target_h))
    scale = fmt(max(zoom, 1.001))

    keyframes = camera.get("keyframes")
    if mode == "keyframed" and isinstance(keyframes, list) and keyframes:
        return _keyframed_camera_filters(keyframes, float(target_w), float(target_h), fallback_zoom=max(zoom, 1.001))

    if mode in {"dynamic_zoom", "push_in"}:
        raw = f"min(t/{fmt(move_duration)},1)"
        progress = escape_expr(f"({raw})*({raw})*(3-2*({raw}))")
        zoom_expr = f"1+({fmt(zoom - 1)})*{progress}"
        return [
            f"scale=w={w}*{zoom_expr}:h={h}*{zoom_expr}:eval=frame",
            f"crop=w={w}:h={h}:x=(iw-{w})/2:y=(ih-{h})/2",
        ]
    if mode in {"handheld", "camera_shake"}:
        amp_x = fmt(10 * intensity)
        amp_y = fmt(7 * intensity)
        return [
            f"scale=w={w}*{scale}:h={h}*{scale}:eval=frame",
            f"crop=w={w}:h={h}:x=(iw-{w})/2+{amp_x}*sin(t*11)+{fmt(pan_x)}:y=(ih-{h})/2+{amp_y}*cos(t*9)+{fmt(pan_y)}",
        ]
    if mode in {"pan", "smooth_pan"}:
        raw = f"min(t/{fmt(move_duration)},1)"
        progress = escape_expr(f"({raw})*({raw})*(3-2*({raw}))")
        return [
            f"scale=w={w}*{scale}:h={h}*{scale}:eval=frame",
            f"crop=w={w}:h={h}:x=(iw-{w})/2+({fmt(pan_x)})*{progress}:y=(ih-{h})/2+({fmt(pan_y)})*{progress}",
        ]
    if mode in {"parallax", "depth"}:
        amp_x = fmt(16 * intensity)
        amp_y = fmt(9 * intensity)
        return [
            f"scale=w={w}*{scale}:h={h}*{scale}:eval=frame",
            f"crop=w={w}:h={h}:x=(iw-{w})/2+{amp_x}*sin(t*0.7):y=(ih-{h})/2+{amp_y}*cos(t*0.55)",
            f"unsharp=5:5:{fmt(0.3 + intensity * 0.35)}",
        ]

    amp_x = fmt(8 * intensity)
    amp_y = fmt(5 * intensity)
    return [
        f"scale=w={w}*{scale}:h={h}*{scale}:eval=frame",
        f"crop=w={w}:h={h}:x=(iw-{w})/2+{amp_x}*sin(t*0.55)+{fmt(pan_x)}:y=(ih-{h})/2+{amp_y}*cos(t*0.42)+{fmt(pan_y)}",
    ]


def _keyframed_camera_filters(keyframes: list[dict[str, Any]], target_w: float, target_h: float, *, fallback_zoom: float) -> list[str]:
    clean = sorted(
        (
            {
                "time": max(float(item.get("time", 0) or 0), 0),
                "x": max(0.0, min(float(item.get("x", 0.5) or 0.5), 1.0)),
                "y": max(0.0, min(float(item.get("y", 0.5) or 0.5), 1.0)),
                "zoom": max(float(item.get("zoom", fallback_zoom) or fallback_zoom), 1.001),
            }
            for item in keyframes
            if isinstance(item, dict)
        ),
        key=lambda item: item["time"],
    )
    if not clean:
        return []
    if len(clean) == 1:
        clean.append({**clean[0], "time": clean[0]["time"] + 0.001})
    zoom_expr = _piecewise_expr(clean, "zoom")
    x_focus = _piecewise_expr(clean, "x")
    y_focus = _piecewise_expr(clean, "y")
    w = fmt(target_w)
    h = fmt(target_h)
    return [
        f"scale=w={w}*({zoom_expr}):h={h}*({zoom_expr}):eval=frame",
        f"crop=w={w}:h={h}:x=(iw-{w})*({x_focus}):y=(ih-{h})*({y_focus})",
    ]


def _piecewise_expr(keyframes: list[dict[str, float]], field: str) -> str:
    expr = fmt(float(keyframes[-1][field]))
    for left, right in reversed(list(zip(keyframes, keyframes[1:]))):
        start = float(left["time"])
        end = max(float(right["time"]), start + 0.001)
        raw = f"min(max((t-{fmt(start)})/{fmt(end - start)},0),1)"
        eased = f"({raw})*({raw})*(3-2*({raw}))"
        value = f"{fmt(float(left[field]))}+({fmt(float(right[field]) - float(left[field]))})*({eased})"
        expr = f"if(lt(t,{fmt(end)}),{value},{expr})"
    return escape_expr(expr)
