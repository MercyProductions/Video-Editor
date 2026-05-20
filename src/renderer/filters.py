from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any


def seconds(value: Any, default: float = 0) -> float:
    if value is None:
        return default
    return float(value)


def fmt(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-9):
        return str(int(round(value)))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def ffmpeg_color(value: str | None, default: str = "#000000", alpha: float | None = None) -> str:
    color = value or default
    if not isinstance(color, str):
        color = default
    if color.startswith("#"):
        raw = color[1:]
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        parsed_alpha = None
        if len(raw) == 8:
            parsed_alpha = int(raw[6:8], 16) / 255
            raw = raw[:6]
        if len(raw) == 6 and re.fullmatch(r"[0-9a-fA-F]{6}", raw):
            suffix_alpha = alpha if alpha is not None else parsed_alpha
            suffix = f"@{fmt(suffix_alpha)}" if suffix_alpha is not None else ""
            return f"0x{raw}{suffix}"
    if alpha is not None and "@" not in color:
        return f"{color}@{fmt(alpha)}"
    return color


def escape_text(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("%", "\\%")
        .replace("\n", "\\n")
    )


def escape_expr(value: str) -> str:
    return value.replace(",", "\\,")


def filter_path(path: Path) -> str:
    normalized = str(path.resolve()).replace("\\", "/")
    return normalized.replace(":", "\\:")


def default_font_file() -> Path | None:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def font_option(font_family: str | None) -> str:
    if font_family:
        candidate = Path(font_family)
        if candidate.exists():
            return f"fontfile='{filter_path(candidate)}'"
        return f"font='{escape_text(font_family)}'"

    fallback = default_font_file()
    if fallback:
        return f"fontfile='{filter_path(fallback)}'"
    return "font='Arial'"


def position_expr(value: Any, axis: str, mode: str) -> str:
    main = "main_w" if mode == "overlay" and axis == "x" else "main_h"
    child = "overlay_w" if mode == "overlay" and axis == "x" else "overlay_h"
    if mode == "text":
        main = "w" if axis == "x" else "h"
        child = "text_w" if axis == "x" else "text_h"

    if value is None:
        value = "center"

    if isinstance(value, (int, float)):
        return fmt(float(value))

    raw = str(value).strip()
    lower = raw.lower()
    if lower in {"center", "middle"}:
        return f"({main}-{child})/2"
    if axis == "x":
        if lower == "left":
            return "0"
        if lower == "right":
            return f"{main}-{child}"
    if axis == "y":
        if lower == "top":
            return "0"
        if lower == "bottom":
            return f"{main}-{child}"
    if raw.endswith("%"):
        return f"{main}*{fmt(float(raw[:-1]) / 100)}"
    return raw


def animation_config(layer: dict[str, Any]) -> dict[str, Any]:
    animation = layer.get("animation")
    if isinstance(animation, str):
        return {"in": animation}
    if isinstance(animation, dict):
        return animation
    return {}


def effect_names(layer: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    animation = animation_config(layer)
    for key in ("in", "out"):
        if animation.get(key):
            names.add(str(animation[key]))

    effects = layer.get("effects")
    if isinstance(effects, str):
        names.add(effects)
    elif isinstance(effects, list):
        names.update(str(effect) for effect in effects)
    return names


def layer_window(layer: dict[str, Any], scene_duration: float) -> tuple[float, float, float]:
    start = seconds(layer.get("start"), 0)
    duration = seconds(layer.get("duration"), max(scene_duration - start, 0))
    end = min(start + duration, scene_duration)
    return start, max(end - start, 0), end


def animated_position(
    layer: dict[str, Any],
    axis: str,
    base_expr: str,
    *,
    start: float,
    duration: float,
    mode: str,
) -> str:
    animation = animation_config(layer)
    names = effect_names(layer)
    expr = base_expr
    end = start + duration
    default_d = seconds(animation.get("duration"), 0.6)
    in_d = seconds(animation.get("inDuration"), default_d)
    out_d = seconds(animation.get("outDuration"), default_d)
    child = "overlay_w" if axis == "x" else "overlay_h"
    if mode == "text":
        child = "text_w" if axis == "x" else "text_h"

    in_name = str(animation.get("in", ""))
    if in_name.startswith("slide") and in_d > 0:
        offset = _slide_offset(in_name, axis, child, entering=True)
        if offset:
            progress = f"(t-{fmt(start)})/{fmt(in_d)}"
            expr = f"if(lt(t,{fmt(start + in_d)}),({expr})+({offset})*(1-({progress})),({expr}))"

    out_name = str(animation.get("out", ""))
    if out_name.startswith("slide") and out_d > 0 and duration > out_d:
        offset = _slide_offset(out_name, axis, child, entering=False)
        if offset:
            progress = f"(t-{fmt(end - out_d)})/{fmt(out_d)}"
            expr = f"if(gte(t,{fmt(end - out_d)}),({base_expr})+({offset})*({progress}),({expr}))"

    if "shake" in names:
        if axis == "x":
            expr = f"({expr})+10*sin(t*60)"
        else:
            expr = f"({expr})+6*cos(t*55)"
    return escape_expr(expr)


def _slide_offset(name: str, axis: str, child: str, *, entering: bool) -> str | None:
    offsets = {
        "slideUp": {"x": None, "y": child if entering else f"-{child}"},
        "slideDown": {"x": None, "y": f"-{child}" if entering else child},
        "slideLeft": {"x": child if entering else f"-{child}", "y": None},
        "slideRight": {"x": f"-{child}" if entering else child, "y": None},
    }
    return offsets.get(name, {}).get(axis)


def alpha_expression(layer: dict[str, Any], start: float, duration: float) -> str | None:
    animation = animation_config(layer)
    end = start + duration
    default_d = seconds(animation.get("duration"), 0.6)
    in_d = seconds(animation.get("inDuration"), default_d)
    out_d = seconds(animation.get("outDuration"), default_d)

    fade_in = animation.get("in") == "fade"
    fade_out = animation.get("out") == "fade"
    if not fade_in and not fade_out:
        return None

    expr = "1"
    if fade_in and in_d > 0:
        expr = f"if(lt(t,{fmt(start + in_d)}),(t-{fmt(start)})/{fmt(in_d)},1)"
    if fade_out and out_d > 0 and duration > out_d:
        expr = f"if(gte(t,{fmt(end - out_d)}),({fmt(end)}-t)/{fmt(out_d)},{expr})"
    return escape_expr(f"max(0,min(1,{expr}))")
