from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


SHOWCASE_STYLES: dict[str, dict[str, Any]] = {
    "cinematic_tech_trailer": {
        "name": "Cinematic Tech Trailer",
        "background": "#05070d",
        "accent": "#38bdf8",
        "textColor": "#f8fafc",
        "mutedText": "#b6c3d1",
        "boxColor": "#020617cc",
        "effectGraphPreset": "cinematic_polish",
        "transition": {"type": "crossfade", "duration": 0.48},
        "cameraMovement": "cinematic_sway",
        "pace": "medium_fast",
        "sceneDuration": 3.6,
        "lightingIntensity": 0.32,
        "transitionIntensity": 0.45,
        "zoomAggressiveness": 0.28,
        "cinematicIntensity": 0.55,
        "captionStyle": "clean",
        "audioVolume": 0.34,
    },
    "premium_saas_showcase": {
        "name": "Premium SaaS Showcase",
        "background": "#070a12",
        "accent": "#60a5fa",
        "textColor": "#ffffff",
        "mutedText": "#cbd5e1",
        "boxColor": "#0f172acc",
        "effectGraphPreset": "cinematic_polish",
        "transition": {"type": "crossfade", "duration": 0.55},
        "cameraMovement": "smooth_pan",
        "pace": "medium",
        "sceneDuration": 4.4,
        "lightingIntensity": 0.22,
        "transitionIntensity": 0.34,
        "zoomAggressiveness": 0.22,
        "cinematicIntensity": 0.45,
        "captionStyle": "premium",
        "audioVolume": 0.28,
    },
    "hacker_cyber": {
        "name": "Hacker/Cyber Aesthetic",
        "background": "#050000",
        "accent": "#ef4444",
        "textColor": "#ffffff",
        "mutedText": "#fecaca",
        "boxColor": "#150505dd",
        "effectGraphPreset": "premium_red_black",
        "transition": {"type": "fadeToBlack", "duration": 0.32},
        "cameraMovement": "smooth_pan",
        "pace": "fast",
        "sceneDuration": 3.1,
        "lightingIntensity": 0.52,
        "transitionIntensity": 0.62,
        "zoomAggressiveness": 0.42,
        "cinematicIntensity": 0.7,
        "captionStyle": "bold",
        "audioVolume": 0.36,
    },
    "gaming_product_showcase": {
        "name": "Gaming Product Showcase",
        "background": "#09020b",
        "accent": "#f97316",
        "textColor": "#ffffff",
        "mutedText": "#fed7aa",
        "boxColor": "#111827d9",
        "effectGraphPreset": "premium_red_black",
        "transition": {"type": "zoom", "duration": 0.25},
        "cameraMovement": "handheld",
        "pace": "fast",
        "sceneDuration": 2.7,
        "lightingIntensity": 0.42,
        "transitionIntensity": 0.72,
        "zoomAggressiveness": 0.5,
        "cinematicIntensity": 0.62,
        "captionStyle": "bold",
        "audioVolume": 0.4,
    },
    "luxury_ui_reveal": {
        "name": "Luxury UI Reveal",
        "background": "#090806",
        "accent": "#f5d46b",
        "textColor": "#fff7db",
        "mutedText": "#e7d9ad",
        "boxColor": "#090806dd",
        "effectGraphPreset": "soft_luxury",
        "transition": {"type": "crossfade", "duration": 0.72},
        "cameraMovement": "cinematic_sway",
        "pace": "slow",
        "sceneDuration": 5.2,
        "lightingIntensity": 0.2,
        "transitionIntensity": 0.28,
        "zoomAggressiveness": 0.18,
        "cinematicIntensity": 0.5,
        "captionStyle": "premium",
        "audioVolume": 0.24,
    },
    "minimalist_product_reveal": {
        "name": "Minimalist Product Reveal",
        "background": "#f8fafc",
        "accent": "#111827",
        "textColor": "#0f172a",
        "mutedText": "#475569",
        "boxColor": "#ffffffdd",
        "effectGraphPreset": "cinematic_polish",
        "transition": {"type": "crossfade", "duration": 0.45},
        "cameraMovement": "smooth_pan",
        "pace": "medium",
        "sceneDuration": 4.8,
        "lightingIntensity": 0.1,
        "transitionIntensity": 0.2,
        "zoomAggressiveness": 0.14,
        "cinematicIntensity": 0.28,
        "captionStyle": "clean",
        "audioVolume": 0.22,
    },
}

ALIASES = {
    "auto": "cinematic_tech_trailer",
    "premium_tech": "cinematic_tech_trailer",
    "tech": "cinematic_tech_trailer",
    "cinematic tech": "cinematic_tech_trailer",
    "premium saas": "premium_saas_showcase",
    "saas": "premium_saas_showcase",
    "cyber": "hacker_cyber",
    "premium cyber": "hacker_cyber",
    "premium_cyber": "hacker_cyber",
    "cybersecurity": "hacker_cyber",
    "hacker": "hacker_cyber",
    "red black": "hacker_cyber",
    "red/black": "hacker_cyber",
    "gaming": "gaming_product_showcase",
    "luxury": "luxury_ui_reveal",
    "apple": "luxury_ui_reveal",
    "minimal": "minimalist_product_reveal",
    "minimalist": "minimalist_product_reveal",
}


def list_showcase_styles() -> list[str]:
    return sorted(SHOWCASE_STYLES)


def resolve_showcase_style(style: str | None, instructions: str = "", overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    if overrides and overrides.get("style") and (not style or _style_key(style) == "auto"):
        style = str(overrides["style"])
    key = _style_key(style or "")
    if key == "auto":
        key = style_from_instructions(instructions)
    if key not in SHOWCASE_STYLES:
        valid = ", ".join(list_showcase_styles())
        raise ValueError(f"Unknown showcase style '{style}'. Valid styles: auto, {valid}")
    profile = deepcopy(SHOWCASE_STYLES[key])
    profile["key"] = key
    if overrides:
        overrides = _normalize_overrides(overrides)
        profile = _deep_merge(profile, overrides)
        profile["key"] = str(overrides.get("style", profile.get("key", key))).strip().lower().replace(" ", "_")
    return profile


def load_style_profile(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    candidate = Path(value)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    stripped = value.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    return {"style": stripped}


def style_from_instructions(instructions: str) -> str:
    text = instructions.lower()
    if any(term in text for term in ("cyber", "security", "hacker", "red lighting", "red/black", "red black")):
        return "hacker_cyber"
    if any(term in text for term in ("game", "gaming", "fast", "aggressive")):
        return "gaming_product_showcase"
    if any(term in text for term in ("apple", "luxury", "premium reveal", "elegant")):
        return "luxury_ui_reveal"
    if any(term in text for term in ("minimal", "simple", "clean", "quiet")):
        return "minimalist_product_reveal"
    if any(term in text for term in ("saas", "dashboard", "business", "b2b")):
        return "premium_saas_showcase"
    return "cinematic_tech_trailer"


def _style_key(value: str) -> str:
    raw = value.strip().lower()
    if not raw:
        return "auto"
    if raw in ALIASES:
        return ALIASES[raw]
    return raw.replace("-", "_").replace(" ", "_").replace("/", "_")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalize_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(overrides)
    camera = str(normalized.get("cameraMovement", "")).strip().lower()
    if camera == "smooth":
        normalized["cameraMovement"] = "smooth_pan"
    lighting = normalized.get("lighting")
    if isinstance(lighting, str):
        text = lighting.lower()
        if "red" in text:
            normalized.setdefault("accent", "#ef4444")
            normalized.setdefault("effectGraphPreset", "premium_red_black")
        if "soft" in text:
            normalized.setdefault("lightingIntensity", 0.28)
        if "glow" in text:
            normalized.setdefault("lightingIntensity", max(float(normalized.get("lightingIntensity", 0.0) or 0.0), 0.42))
    elif isinstance(lighting, dict):
        if lighting.get("intensity") is not None:
            normalized["lightingIntensity"] = lighting["intensity"]
        theme = str(lighting.get("theme", "")).lower()
        if "red" in theme:
            normalized.setdefault("accent", "#ef4444")
            normalized.setdefault("effectGraphPreset", "premium_red_black")
    return normalized
