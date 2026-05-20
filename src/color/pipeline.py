from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


COLOR_PRESETS: dict[str, dict[str, Any]] = {
    "clean_cinematic": {
        "label": "Clean Cinematic",
        "nodes": [
            {"type": "color_grade", "brightness": -0.01, "contrast": 1.07, "saturation": 1.04},
            {"type": "split_tone", "shadows": "#0f172a", "highlights": "#f8fafc", "amount": 0.08},
            {"type": "vignette", "intensity": 0.25},
        ],
    },
    "premium_red_black": {
        "label": "Premium Red/Black",
        "nodes": [
            {"type": "color_grade", "brightness": -0.035, "contrast": 1.14, "saturation": 1.08},
            {"type": "tint", "color": "#ef4444", "opacity": 0.055},
            {"type": "glow", "amount": 0.22},
            {"type": "vignette", "intensity": 0.38},
        ],
    },
    "soft_luxury": {
        "label": "Soft Luxury",
        "nodes": [
            {"type": "color_grade", "brightness": 0.012, "contrast": 1.04, "saturation": 0.96},
            {"type": "tint", "color": "#f5d46b", "opacity": 0.04},
            {"type": "vignette", "intensity": 0.2},
        ],
    },
    "social_punch": {
        "label": "Social Punch",
        "nodes": [
            {"type": "color_grade", "brightness": 0.005, "contrast": 1.18, "saturation": 1.14},
            {"type": "glow", "amount": 0.18},
            {"type": "vignette", "intensity": 0.28},
        ],
    },
}


def list_color_presets() -> list[dict[str, Any]]:
    return [{"key": key, **value} for key, value in sorted(COLOR_PRESETS.items())]


def list_luts(root: Path | None = None) -> list[dict[str, Any]]:
    lut_root = root or Path(__file__).resolve().parents[2] / "luts"
    if not lut_root.exists():
        return []
    rows = []
    for path in sorted(lut_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".cube", ".3dl"}:
            rows.append({"name": path.stem, "path": str(path.resolve()), "extension": path.suffix.lower()})
    return rows


def apply_color_pipeline(project: dict[str, Any], preset: str, *, lut_path: Path | None = None) -> dict[str, Any]:
    key = preset.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in COLOR_PRESETS:
        valid = ", ".join(sorted(COLOR_PRESETS))
        raise ValueError(f"Unknown color preset '{preset}'. Valid presets: {valid}")
    colored = deepcopy(project)
    nodes = [dict(node) for node in COLOR_PRESETS[key]["nodes"]]
    if lut_path:
        nodes.append({"type": "lut", "path": str(lut_path)})
    for scene in colored.get("timeline", []):
        graph = scene.setdefault("effectGraph", {})
        existing = graph.get("nodes", []) if isinstance(graph, dict) else []
        if not isinstance(existing, list):
            existing = []
        scene["effectGraph"] = {"nodes": [*nodes, *[node for node in existing if isinstance(node, dict)]]}
        post = scene.setdefault("postProcessing", {})
        post.setdefault("colorPipeline", key)
        post.setdefault("exportColorSpace", "rec709")
        post.setdefault("toneMapping", "sdr-safe")
    colored.setdefault("metadata", {}).setdefault("phase11", {})["colorPipeline"] = {
        "preset": key,
        "lut": str(lut_path.resolve()) if lut_path else None,
        "workflow": "Rec.709 SDR-safe FFmpeg filter chain",
    }
    return colored
