from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_PROFILE: dict[str, Any] = {
    "name": "Default Creator",
    "introStyle": "short_title_card",
    "captionStyle": {
        "fontSize": 58,
        "color": "#ffffff",
        "strokeColor": "#000000",
        "strokeWidth": 4,
        "box": True,
        "boxColor": "#000000aa",
        "boxPadding": 16,
    },
    "preferredMusicBehavior": {"volume": 0.42, "fadeIn": 0.2, "fadeOut": 1.0, "loop": True},
    "transitionFrequency": "scene",
    "exportSettings": {"preset": "shorts", "quality": "preview"},
    "timelineBehavior": {"snapSeconds": 0.25, "rippleEdits": True, "zoomLevel": 1.0},
    "favoriteTransitions": ["cut", "crossfade"],
    "renderDefaults": {"cache": True, "resume": True, "gpu": False},
    "branding": {"logo": None, "primaryColor": "#ef4444", "secondaryColor": "#050000"},
    "ctaStyle": "quick_direct",
}


def profile_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "profiles"


def profile_path(name: str) -> Path:
    return profile_dir() / f"{_slug(name)}.creator-profile.json"


def create_profile(name: str, *, output_path: Path | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = {**DEFAULT_PROFILE, "name": name}
    if overrides:
        profile.update(overrides)
    path = output_path or profile_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    profile["path"] = str(path.resolve())
    return profile


def load_profile(path_or_name: str | Path | None) -> dict[str, Any]:
    if not path_or_name:
        return dict(DEFAULT_PROFILE)
    path = Path(path_or_name)
    if not path.exists():
        path = profile_path(str(path_or_name))
    if not path.exists():
        return {**DEFAULT_PROFILE, "name": str(path_or_name)}
    profile = json.loads(path.read_text(encoding="utf-8"))
    return {**DEFAULT_PROFILE, **profile, "path": str(path.resolve())}


def list_profiles() -> list[dict[str, Any]]:
    root = profile_dir()
    if not root.exists():
        return []
    profiles = []
    for path in sorted(root.glob("*.creator-profile.json")):
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
            profile["path"] = str(path.resolve())
            profiles.append(profile)
        except json.JSONDecodeError:
            continue
    return profiles


def apply_profile_to_project(project: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(project))
    export_settings = profile.get("exportSettings", {})
    if export_settings.get("preset"):
        updated["exportPreset"] = export_settings["preset"]
    updated.setdefault("metadata", {}).setdefault("creatorProfile", {})["name"] = profile.get("name", "Default Creator")
    updated["metadata"]["creatorProfile"]["timelineBehavior"] = profile.get("timelineBehavior", DEFAULT_PROFILE["timelineBehavior"])
    updated["metadata"]["creatorProfile"]["favoriteTransitions"] = profile.get("favoriteTransitions", DEFAULT_PROFILE["favoriteTransitions"])
    updated["metadata"]["creatorProfile"]["renderDefaults"] = profile.get("renderDefaults", DEFAULT_PROFILE["renderDefaults"])
    caption_style = profile.get("captionStyle", DEFAULT_PROFILE["captionStyle"])
    for scene in updated.get("timeline", []):
        for layer in scene.get("layers", []):
            if layer.get("type") in {"caption", "captions"}:
                for key, value in caption_style.items():
                    layer.setdefault(key, value)
    for track in updated.get("audio", []):
        for key, value in profile.get("preferredMusicBehavior", DEFAULT_PROFILE["preferredMusicBehavior"]).items():
            track.setdefault(key, value)
    return updated


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "creator"
