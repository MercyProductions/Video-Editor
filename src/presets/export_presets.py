from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ExportPreset:
    key: str
    label: str
    width: int
    height: int
    fps: int
    crf: int
    description: str
    container: str = "mp4"
    video_codec: str = "h264"
    audio_codec: str = "aac"


EXPORT_PRESETS: dict[str, ExportPreset] = {
    "youtube_1080p": ExportPreset(
        key="youtube_1080p",
        label="YouTube 1920x1080 60fps",
        width=1920,
        height=1080,
        fps=60,
        crf=18,
        description="Standard 16:9 YouTube upload.",
    ),
    "tiktok_reels": ExportPreset(
        key="tiktok_reels",
        label="TikTok/Reels 1080x1920 60fps",
        width=1080,
        height=1920,
        fps=60,
        crf=19,
        description="Vertical short-form video for TikTok, Instagram Reels, and mobile feeds.",
    ),
    "shorts": ExportPreset(
        key="shorts",
        label="Shorts 1080x1920",
        width=1080,
        height=1920,
        fps=60,
        crf=19,
        description="YouTube Shorts vertical export.",
    ),
    "square": ExportPreset(
        key="square",
        label="Square 1080x1080",
        width=1080,
        height=1080,
        fps=30,
        crf=20,
        description="Square social feed export.",
    ),
    "discord_720p": ExportPreset(
        key="discord_720p",
        label="Discord 720p compressed",
        width=1280,
        height=720,
        fps=30,
        crf=28,
        description="Smaller file size for chat sharing.",
    ),
    "cinematic_4k": ExportPreset(
        key="cinematic_4k",
        label="Cinematic 4K",
        width=3840,
        height=2160,
        fps=24,
        crf=16,
        description="High-quality 4K cinematic timeline.",
    ),
    "instagram_reels": ExportPreset(
        key="instagram_reels",
        label="Instagram Reels 1080x1920 60fps",
        width=1080,
        height=1920,
        fps=60,
        crf=19,
        description="Vertical Instagram Reels export with the same geometry as TikTok/Reels.",
    ),
    "high_quality_archive": ExportPreset(
        key="high_quality_archive",
        label="High Quality Archive",
        width=3840,
        height=2160,
        fps=60,
        crf=14,
        description="High-quality local archive master for future repurposing.",
        container="mov",
    ),
    "low_size_preview": ExportPreset(
        key="low_size_preview",
        label="Low Size Preview",
        width=1280,
        height=720,
        fps=30,
        crf=32,
        description="Small preview export for quick review and sharing.",
    ),
}


ALIASES = {
    "youtube": "youtube_1080p",
    "youtube_1920x1080": "youtube_1080p",
    "tiktok": "tiktok_reels",
    "reels": "tiktok_reels",
    "reel": "tiktok_reels",
    "instagram": "instagram_reels",
    "ig": "instagram_reels",
    "archive": "high_quality_archive",
    "high_quality": "high_quality_archive",
    "preview": "low_size_preview",
    "low_size": "low_size_preview",
    "short": "shorts",
    "shorts_1080x1920": "shorts",
    "square_1080": "square",
    "discord": "discord_720p",
    "720p": "discord_720p",
    "4k": "cinematic_4k",
    "cinematic": "cinematic_4k",
}


def normalize_preset_key(key: str | None) -> str | None:
    if not key:
        return None
    normalized = key.strip().lower().replace("-", "_").replace(" ", "_")
    return ALIASES.get(normalized, normalized)


def get_export_preset(key: str | None) -> ExportPreset | None:
    normalized = normalize_preset_key(key)
    if not normalized:
        return None
    if normalized not in EXPORT_PRESETS:
        valid = ", ".join(sorted(EXPORT_PRESETS))
        raise ValueError(f"Unknown export preset '{key}'. Valid presets: {valid}")
    return EXPORT_PRESETS[normalized]


def list_export_presets() -> list[ExportPreset]:
    return list(EXPORT_PRESETS.values())


def apply_export_preset(project_settings: dict[str, Any], preset_key: str | None) -> dict[str, Any]:
    settings = dict(project_settings)
    preset = get_export_preset(preset_key or settings.get("exportPreset") or settings.get("preset"))
    if not preset:
        settings.setdefault("width", 1920)
        settings.setdefault("height", 1080)
        settings.setdefault("fps", 30)
        settings.setdefault("crf", 18)
        return settings

    settings["width"] = preset.width
    settings["height"] = preset.height
    settings["fps"] = preset.fps
    settings["crf"] = preset.crf
    settings["exportPreset"] = preset.key
    return settings
