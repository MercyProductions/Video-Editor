from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from showcase.styles import style_from_instructions


def load_manual_overrides(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    candidate = Path(value)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    stripped = value.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    raise ValueError(f"Manual override must be a JSON file or inline JSON object: {value}")


def interpret_showcase_spec(
    instructions: str,
    *,
    manual_overrides: dict[str, Any] | None = None,
    product_name: str | None = None,
    requested_duration: float | None = None,
    requested_style: str | None = None,
    music_available: bool = False,
) -> dict[str, Any]:
    text = instructions.strip()
    lowered = text.lower()
    spec: dict[str, Any] = {
        "format": "automatic-video-editor-showcase-spec",
        "createdAt": _now(),
        "productName": product_name or _extract_product_name(text),
        "style": requested_style if requested_style and requested_style != "auto" else style_from_instructions(text),
        "duration": requested_duration or _extract_duration(lowered),
        "musicSync": music_available and "no music sync" not in lowered,
        "mustShow": _extract_focus_targets(text),
        "cutOut": _extract_cut_out(lowered),
        "pace": _extract_pace(lowered),
        "lighting": _extract_lighting(lowered),
        "audio": _extract_audio(lowered),
        "visualEnhancement": {
            "cinematicCrop": True,
            "smoothZooms": "zoom" in lowered or "smooth" in lowered or "cinematic" in lowered,
            "cursorSpotlight": True,
            "backgroundDim": "dark" in lowered or "cyber" in lowered or "premium" in lowered,
            "accentGlow": "glow" in lowered or "red" in lowered or "futuristic" in lowered,
            "vignette": True,
            "depthShadow": True,
            "contrastTuning": True,
            "textReadabilityProtection": True,
        },
        "titleCards": _title_cards_from_targets(_extract_focus_targets(text)),
        "constraints": {
            "avoidCuttingMenus": True,
            "preserveReadability": True,
            "preferFocusCentered": True,
            "removeMistakes": True,
        },
        "reasoning": _reasoning_summary(lowered),
    }
    if manual_overrides:
        spec = _apply_manual_overrides(spec, manual_overrides)
    if not spec.get("duration"):
        spec["duration"] = 45 if "short" in lowered else None
    return spec


def _apply_manual_overrides(spec: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(spec)
    for key, value in overrides.items():
        normalized_key = "style" if key == "stylePreset" else key
        if isinstance(value, dict) and isinstance(merged.get(normalized_key), dict):
            merged[normalized_key] = {**merged[normalized_key], **value}
        else:
            merged[normalized_key] = value
    if "duration" in overrides:
        merged["duration"] = overrides["duration"]
    if "mustShow" in overrides:
        merged["mustShow"] = [str(item) for item in overrides.get("mustShow", [])]
        merged["titleCards"] = _title_cards_from_targets(merged["mustShow"])
    if "cutOut" in overrides:
        merged["cutOut"] = [str(item) for item in overrides.get("cutOut", [])]
    if isinstance(overrides.get("lighting"), dict):
        lighting = dict(merged.get("lighting", {}))
        lighting.update(overrides["lighting"])
        merged["lighting"] = lighting
    return merged


def _extract_duration(text: str) -> float | None:
    match = re.search(r"(?:under|about|around|make it|create a)?\s*(\d{1,3})(?:\s|-)?(?:second|sec|s)\b", text)
    if match:
        return float(match.group(1))
    match = re.search(r"(\d{1,3})\s*(?:to|-)\s*(\d{1,3})\s*(?:second|sec|s)", text)
    if match:
        return float(match.group(2))
    return None


def _extract_product_name(text: str) -> str | None:
    match = re.search(r"(?:for|about)\s+(?:my\s+|the\s+)?([A-Za-z0-9][A-Za-z0-9 _-]{2,60}?)(?:\.|,| with | that |$)", text)
    if match:
        return match.group(1).strip()
    return None


def _extract_focus_targets(text: str) -> list[str]:
    lowered = text.lower()
    match = re.search(r"focus (?:heavily )?(?:on|around)\s+(.+?)(?:\.|$)", text, re.IGNORECASE)
    if match:
        return _split_targets(match.group(1))
    targets = []
    for keyword in ("login", "dashboard", "scan results", "settings", "analytics", "success", "report", "checkout", "editor", "timeline"):
        if keyword in lowered:
            targets.append(keyword)
    return _dedupe(targets)


def _extract_cut_out(text: str) -> list[str]:
    targets = []
    for pattern in (r"cut out\s+(.+?)(?:\.|$)", r"remove\s+(.+?)(?:\.|$)", r"avoid\s+(.+?)(?:\.|$)"):
        match = re.search(pattern, text)
        if match:
            targets.extend(_split_targets(match.group(1)))
    for keyword in ("desktop idle", "file explorer", "alt-tabbing", "wrong window", "loading waits", "failed clicks", "long pauses", "repeated attempts"):
        if keyword in text:
            targets.append(keyword)
    if "no loud effects" in text:
        targets.append("loud effects")
    return _dedupe(targets)


def _extract_pace(text: str) -> str:
    if any(term in text for term in ("fast", "punchy", "aggressive", "high energy")):
        return "fast"
    if any(term in text for term in ("slow", "elegant", "minimal", "calm")):
        return "slow"
    if "medium fast" in text or "medium-fast" in text:
        return "medium_fast"
    return "medium_fast" if "showcase" in text or "trailer" in text else "medium"


def _extract_lighting(text: str) -> dict[str, Any]:
    theme = "neutral"
    if "red/black" in text or "red black" in text or "cyber" in text:
        theme = "red_black"
    elif "blue" in text or "saas" in text:
        theme = "blue_tech"
    elif "luxury" in text or "gold" in text:
        theme = "warm_luxury"
    intensity = 0.32
    if "subtle" in text:
        intensity = 0.24
    if "dark" in text or "glow" in text:
        intensity = max(intensity, 0.45)
    return {"theme": theme, "intensity": round(intensity, 2), "darkening": "dark" in text, "glow": "glow" in text or "futuristic" in text}


def _extract_audio(text: str) -> dict[str, Any]:
    return {
        "loudEffects": "no loud effects" not in text,
        "musicMood": "subtle" if "subtle" in text or "minimal" in text else "cinematic",
        "ducking": True,
        "normalize": True,
    }


def _title_cards_from_targets(targets: list[str]) -> list[dict[str, str]]:
    if not targets:
        return [
            {"title": "Feature Reveal", "benefit": "Show the workflow clearly."},
            {"title": "Result Moment", "benefit": "End on a confident payoff."},
        ]
    return [{"title": _title_case(target), "benefit": _benefit_for_target(target)} for target in targets[:6]]


def _benefit_for_target(target: str) -> str:
    text = target.lower()
    if "login" in text:
        return "Fast access, clean first impression."
    if "dashboard" in text:
        return "The whole workflow becomes easy to scan."
    if "scan" in text:
        return "Issues surface quickly and clearly."
    if "result" in text or "success" in text:
        return "The payoff is obvious."
    return "Keep the viewer focused on the right detail."


def _reasoning_summary(text: str) -> list[str]:
    notes = []
    if "cyber" in text or "red" in text:
        notes.append("Red/black styling and darker lighting fit the requested cybersecurity tone.")
    if "smooth" in text:
        notes.append("Smooth zoom and pan behavior is preferred over aggressive cuts.")
    if "focus" in text:
        notes.append("Named focus targets are promoted into title cards and scene labels.")
    if "no loud effects" in text:
        notes.append("Audio intensity is constrained to keep the edit premium rather than noisy.")
    return notes or ["Spec uses balanced cinematic pacing with readable captions and focused UI framing."]


def _split_targets(value: str) -> list[str]:
    value = re.sub(r"\band\b", ",", value, flags=re.IGNORECASE)
    return _dedupe([item.strip(" .") for item in value.split(",") if item.strip(" .")])


def _dedupe(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        key = value.lower()
        if key not in seen:
            result.append(value)
            seen.add(key)
    return result


def _title_case(value: str) -> str:
    return " ".join(word.capitalize() for word in value.replace("_", " ").split())


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
