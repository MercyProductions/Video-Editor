from __future__ import annotations

from typing import Any


def transition_type(transition: dict[str, Any] | None) -> str:
    if not transition:
        return "cut"
    return str(transition.get("type", "cut"))


def transition_duration(transition: dict[str, Any] | None) -> float:
    if not transition:
        return 0
    return float(transition.get("duration", 0) or 0)


def ffmpeg_xfade_name(transition: dict[str, Any]) -> str:
    kind = transition_type(transition)
    if kind in {"crossfade", "fade"}:
        return "fade"
    if kind == "fadeToBlack":
        return "fadeblack"
    if kind == "zoom":
        return "zoomin"
    if kind == "slide":
        direction = str(transition.get("direction", "left"))
        return {
            "left": "slideleft",
            "right": "slideright",
            "up": "slideup",
            "down": "slidedown",
        }.get(direction, "slideleft")
    return "fade"
