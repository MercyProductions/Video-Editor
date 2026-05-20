from __future__ import annotations

from copy import deepcopy
from typing import Any


STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "clean_cinematic": {
        "background": "#05070d",
        "text": {"color": "#f8fafc", "strokeColor": "#020617", "strokeWidth": 2, "shadowColor": "#000000"},
        "media": {"contrast": 1.08, "brightness": 0.01},
        "transition": {"type": "crossfade", "duration": 0.55},
    },
    "gaming_montage": {
        "background": "#050000",
        "text": {"color": "#ffffff", "strokeColor": "#000000", "strokeWidth": 3, "box": True, "boxColor": "#7f1d1dcc", "boxPadding": 14},
        "media": {"contrast": 1.18},
        "transition": {"type": "zoom", "duration": 0.28},
        "effects": ["shake"],
    },
    "red_black_aegis": {
        "background": "#050000",
        "text": {"color": "#ef4444", "strokeColor": "#000000", "strokeWidth": 3, "shadowColor": "#000000"},
        "media": {"contrast": 1.16, "brightness": -0.02},
        "transition": {"type": "fadeToBlack", "duration": 0.35},
    },
    "blue_black_cyber": {
        "background": "#020617",
        "text": {"color": "#38bdf8", "strokeColor": "#000000", "strokeWidth": 3, "shadowColor": "#000000"},
        "media": {"contrast": 1.12, "brightness": -0.01},
        "transition": {"type": "crossfade", "duration": 0.38},
    },
    "vaporwave": {
        "background": "#17002e",
        "text": {"color": "#67e8f9", "strokeColor": "#f472b6", "strokeWidth": 2, "shadowColor": "#000000"},
        "media": {"contrast": 1.12, "brightness": 0.04},
        "transition": {"type": "slide", "duration": 0.45, "direction": "left"},
    },
    "minimal_tech": {
        "background": "#f8fafc",
        "text": {"color": "#0f172a", "strokeWidth": 0, "box": True, "boxColor": "#ffffffdd", "boxPadding": 12},
        "media": {"contrast": 1.03},
        "transition": {"type": "crossfade", "duration": 0.4},
    },
    "horror_glitch": {
        "background": "#020202",
        "text": {"color": "#f8fafc", "strokeColor": "#7f1d1d", "strokeWidth": 4, "shadowColor": "#000000"},
        "media": {"contrast": 1.35, "brightness": -0.08, "blur": 0.2},
        "transition": {"type": "fadeToBlack", "duration": 0.22},
        "effects": ["shake"],
    },
    "luxury_promo": {
        "background": "#090806",
        "text": {"color": "#f5d46b", "strokeColor": "#000000", "strokeWidth": 1, "shadowColor": "#000000"},
        "media": {"contrast": 1.06, "brightness": 0.02},
        "transition": {"type": "crossfade", "duration": 0.75},
    },
}

ALIASES = {
    "clean cinematic": "clean_cinematic",
    "cinematic": "clean_cinematic",
    "gaming montage": "gaming_montage",
    "gaming": "gaming_montage",
    "red/black aegis": "red_black_aegis",
    "red black aegis": "red_black_aegis",
    "aegis": "red_black_aegis",
    "blue/black cyber": "blue_black_cyber",
    "blue black cyber": "blue_black_cyber",
    "blue_black_cyber": "blue_black_cyber",
    "blue black": "blue_black_cyber",
    "minimal tech": "minimal_tech",
    "horror glitch": "horror_glitch",
    "horror/glitch": "horror_glitch",
    "luxury promo": "luxury_promo",
    "luxury": "luxury_promo",
}


def normalize_style(name: str) -> str:
    normalized = name.strip().lower().replace("-", "_").replace(" ", "_").replace("/", "_")
    return ALIASES.get(name.strip().lower(), normalized)


def list_styles() -> list[str]:
    return sorted(STYLE_PRESETS)


def apply_style(project: dict[str, Any], style_name: str) -> dict[str, Any]:
    key = normalize_style(style_name)
    if key not in STYLE_PRESETS:
        valid = ", ".join(list_styles())
        raise ValueError(f"Unknown style '{style_name}'. Valid styles: {valid}")
    styled = deepcopy(project)
    style = STYLE_PRESETS[key]
    styled.setdefault("project", {})["background"] = style["background"]
    styled.setdefault("metadata", {})["stylePreset"] = key

    for scene in styled.get("timeline", []):
        if scene is not styled.get("timeline", [])[-1]:
            scene["transitionOut"] = dict(style["transition"])
        for layer in scene.get("layers", []):
            if layer.get("type") in {"text", "caption", "captions"}:
                for prop, value in style["text"].items():
                    layer.setdefault(prop, value)
                if style.get("effects") and layer.get("type") == "text":
                    layer["effects"] = sorted(set(layer.get("effects", []) + style["effects"]))
            if layer.get("type") in {"video", "image"}:
                for prop, value in style["media"].items():
                    layer.setdefault(prop, value)
    return styled
