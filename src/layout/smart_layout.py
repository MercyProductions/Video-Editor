from __future__ import annotations

from copy import deepcopy
from typing import Any


def apply_smart_layout(project: dict[str, Any]) -> dict[str, Any]:
    resolved = deepcopy(project)
    width = int(resolved.get("project", {}).get("width", 1920))
    height = int(resolved.get("project", {}).get("height", 1080))
    for scene in resolved.get("timeline", []):
        for index, layer in enumerate(scene.get("layers", [])):
            resolve_layout_layer(layer, width, height, index=index)
    return resolved


def resolve_layout_layer(layer: dict[str, Any], width: int, height: int, *, index: int = 0) -> dict[str, Any]:
    safe = layer.get("safeZone", "title")
    margin = _safe_margin(width, height, safe)
    layout = layer.get("layout") or layer.get("anchor")
    if layout:
        _apply_named_layout(layer, str(layout), width, height, margin, index)
    if layer.get("grid"):
        _apply_grid(layer, layer["grid"], width, height, margin)
    if layer.get("autoFit") and layer.get("type") in {"video", "image"}:
        mode = str(layer.get("autoFit"))
        if mode in {"cover", "contain", "fit"}:
            layer.setdefault("width", width - margin * 2)
            layer.setdefault("height", height - margin * 2)
            layer.setdefault("x", margin)
            layer.setdefault("y", margin)
    return layer


def _safe_margin(width: int, height: int, safe: Any) -> int:
    if isinstance(safe, (int, float)):
        return int(safe)
    if safe == "action":
        return int(min(width, height) * 0.05)
    if safe == "none":
        return 0
    return int(min(width, height) * 0.08)


def _apply_named_layout(layer: dict[str, Any], layout: str, width: int, height: int, margin: int, index: int) -> None:
    if layout in {"center", "center_region"}:
        layer.setdefault("x", "center")
        layer.setdefault("y", "center")
    elif layout == "lower_third":
        layer.setdefault("x", "center")
        layer.setdefault("y", int(height * 0.72))
        if layer.get("type") in {"text", "caption", "captions"}:
            layer.setdefault("box", True)
            layer.setdefault("boxColor", "#00000099")
            layer.setdefault("boxPadding", 14)
    elif layout == "upper_left":
        layer.setdefault("x", margin)
        layer.setdefault("y", margin)
    elif layout == "upper_right":
        layer.setdefault("x", "right")
        layer.setdefault("y", margin)
    elif layout == "bottom":
        layer.setdefault("x", "center")
        layer.setdefault("y", height - margin * 2)
    elif layout == "pip":
        pip_width = int(width * 0.28)
        pip_height = int(height * 0.28)
        layer.setdefault("width", pip_width)
        layer.setdefault("height", pip_height)
        layer.setdefault("x", width - pip_width - margin)
        layer.setdefault("y", height - pip_height - margin)
    elif layout == "split_left":
        layer.setdefault("x", margin)
        layer.setdefault("y", margin)
        layer.setdefault("width", int((width - margin * 3) / 2))
        layer.setdefault("height", height - margin * 2)
    elif layout == "split_right":
        layer.setdefault("x", int(width / 2 + margin / 2))
        layer.setdefault("y", margin)
        layer.setdefault("width", int((width - margin * 3) / 2))
        layer.setdefault("height", height - margin * 2)
    elif layout == "split_screen":
        side = "split_left" if index % 2 == 0 else "split_right"
        _apply_named_layout(layer, side, width, height, margin, index)


def _apply_grid(layer: dict[str, Any], grid: Any, width: int, height: int, margin: int) -> None:
    if not isinstance(grid, dict):
        return
    rows = max(int(grid.get("rows", 1)), 1)
    cols = max(int(grid.get("cols", 1)), 1)
    cell = max(int(grid.get("cell", 0)), 0)
    row = min(max(int(grid.get("row", 0)), 0), rows - 1)
    col = min(max(int(grid.get("col", cell)), 0), cols - 1)
    gap = int(grid.get("gap", margin // 2))
    cell_w = int((width - margin * 2 - gap * (cols - 1)) / cols)
    cell_h = int((height - margin * 2 - gap * (rows - 1)) / rows)
    layer["x"] = margin + col * (cell_w + gap)
    layer["y"] = margin + row * (cell_h + gap)
    if layer.get("type") in {"video", "image"}:
        layer.setdefault("width", cell_w)
        layer.setdefault("height", cell_h)
