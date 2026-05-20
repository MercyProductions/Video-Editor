from __future__ import annotations

from pathlib import Path
from typing import Any

from renderer.filters import ffmpeg_color, filter_path, fmt


EFFECT_GRAPH_PRESETS: dict[str, list[dict[str, Any]]] = {
    "cinematic_polish": [
        {"type": "color_grade", "contrast": 1.04, "brightness": 0.018, "saturation": 1.04},
        {"type": "vignette", "intensity": 0.14},
        {"type": "sharpen", "amount": 0.22},
    ],
    "premium_red_black": [
        {"type": "color_grade", "contrast": 1.07, "brightness": 0.01, "saturation": 1.06},
        {"type": "tint", "color": "#ef4444", "opacity": 0.035},
        {"type": "vignette", "intensity": 0.16},
        {"type": "glow", "amount": 0.14},
    ],
    "soft_luxury": [
        {"type": "color_grade", "contrast": 1.03, "brightness": 0.02, "saturation": 0.98},
        {"type": "tint", "color": "#f5d46b", "opacity": 0.025},
        {"type": "vignette", "intensity": 0.12},
    ],
}


def list_effect_graph_presets() -> list[str]:
    return sorted(EFFECT_GRAPH_PRESETS)


def preset_nodes(name: str) -> list[dict[str, Any]]:
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in EFFECT_GRAPH_PRESETS:
        valid = ", ".join(list_effect_graph_presets())
        raise ValueError(f"Unknown effect graph preset '{name}'. Valid presets: {valid}")
    return [dict(node) for node in EFFECT_GRAPH_PRESETS[key]]


def scene_post_filters(scene: dict[str, Any], project_root: Path | None = None) -> list[str]:
    nodes: list[dict[str, Any]] = []
    preset = scene.get("effectGraphPreset")
    if preset:
        nodes.extend(preset_nodes(str(preset)))
    graph = scene.get("effectGraph")
    if isinstance(graph, dict):
        graph = graph.get("nodes", [])
    if isinstance(graph, list):
        nodes.extend(node for node in graph if isinstance(node, dict))
    post = scene.get("postProcessing")
    if isinstance(post, dict):
        nodes.extend(_post_processing_nodes(post))
    return filters_from_nodes(nodes, project_root=project_root)


def filters_from_nodes(nodes: list[dict[str, Any]], project_root: Path | None = None) -> list[str]:
    filters: list[str] = []
    for node in nodes:
        kind = str(node.get("type", "")).lower()
        if kind in {"color_grade", "eq", "adjustment"}:
            brightness = fmt(float(node.get("brightness", 0) or 0))
            contrast = fmt(float(node.get("contrast", 1) or 1))
            saturation = fmt(float(node.get("saturation", 1) or 1))
            gamma = fmt(float(node.get("gamma", 1) or 1))
            filters.append(f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}")
            if gamma != "1":
                filters.append(f"eq=gamma={gamma}")
        elif kind == "exposure":
            amount = fmt(float(node.get("amount", node.get("value", 0)) or 0))
            filters.append(f"eq=brightness={amount}")
        elif kind == "split_tone":
            shadows = ffmpeg_color(str(node.get("shadows", "#0f172a")))
            highlights = ffmpeg_color(str(node.get("highlights", "#f8fafc")))
            amount = fmt(float(node.get("amount", 0.08) or 0.08))
            filters.append(f"drawbox=x=0:y=0:w=iw:h=ih/2:color={shadows}@{amount}:t=fill")
            filters.append(f"drawbox=x=0:y=ih/2:w=iw:h=ih/2:color={highlights}@{amount}:t=fill")
        elif kind == "vignette":
            angle = fmt(1.5708 * max(float(node.get("intensity", 0.35) or 0.35), 0.05))
            filters.append(f"vignette={angle}")
        elif kind == "sharpen":
            amount = fmt(float(node.get("amount", 0.35) or 0.35))
            filters.append(f"unsharp=5:5:{amount}")
        elif kind in {"blur", "blur_layer"}:
            amount = fmt(float(node.get("amount", node.get("radius", 1.5)) or 1.5))
            filters.append(f"boxblur={amount}")
        elif kind == "glow":
            amount = float(node.get("amount", 0.25) or 0.25)
            filters.append(f"unsharp=7:7:{fmt(0.25 + amount)}")
            filters.append(f"eq=contrast={fmt(1 + amount * 0.16)}:brightness={fmt(amount * 0.01)}")
        elif kind == "tint":
            color = ffmpeg_color(str(node.get("color", "#ef4444")))
            opacity = fmt(float(node.get("opacity", 0.08) or 0.08))
            filters.append(f"drawbox=x=0:y=0:w=iw:h=ih:color={color}@{opacity}:t=fill")
        elif kind == "setparams":
            colorspace = str(node.get("colorspace", "bt709"))
            primaries = str(node.get("color_primaries", node.get("primaries", "bt709")))
            transfer = str(node.get("color_trc", node.get("transfer", "bt709")))
            color_range = str(node.get("range", "tv"))
            filters.append(
                "setparams="
                f"colorspace={colorspace}:"
                f"color_primaries={primaries}:"
                f"color_trc={transfer}:"
                f"range={color_range}"
            )
        elif kind in {"tone_map", "tonemap"}:
            mode = str(node.get("mode", "hable"))
            desat = fmt(float(node.get("desat", 0.2) or 0.2))
            filters.extend(
                [
                    "zscale=t=linear:npl=100,format=gbrpf32le",
                    f"tonemap=tonemap={mode}:desat={desat}",
                    "zscale=t=bt709:m=bt709:r=tv,format=rgba",
                ]
            )
        elif kind in {"lut", "lut3d"} and node.get("path"):
            lut_path = Path(str(node["path"]))
            if not lut_path.is_absolute() and project_root:
                lut_path = project_root / lut_path
            filters.append(f"lut3d=file='{filter_path(lut_path)}'")
        elif kind == "lut_stack":
            for item in node.get("paths", []):
                lut_path = Path(str(item))
                if not lut_path.is_absolute() and project_root:
                    lut_path = project_root / lut_path
                filters.append(f"lut3d=file='{filter_path(lut_path)}'")
    return filters


def _post_processing_nodes(post: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if post.get("colorGrade"):
        color = post["colorGrade"]
        if isinstance(color, dict):
            nodes.append({"type": "color_grade", **color})
    if post.get("vignette"):
        value = post["vignette"]
        nodes.append({"type": "vignette", "intensity": value if isinstance(value, (int, float)) else 0.35})
    if post.get("glow") or post.get("bloom"):
        nodes.append({"type": "glow", "amount": post.get("glow") or post.get("bloom") or 0.25})
    if post.get("exposure"):
        nodes.append({"type": "exposure", "amount": post["exposure"]})
    if post.get("lut"):
        nodes.append({"type": "lut", "path": post["lut"]})
    if post.get("colorManagement"):
        color = post["colorManagement"]
        if isinstance(color, dict):
            nodes.append(
                {
                    "type": "setparams",
                    "colorspace": color.get("exportColorSpace", "bt709"),
                    "color_primaries": color.get("primaries", "bt709"),
                    "color_trc": color.get("transfer", "bt709"),
                    "range": color.get("range", "tv"),
                }
            )
    return nodes
