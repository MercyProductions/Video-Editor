from __future__ import annotations

from pathlib import Path
from typing import Any

from assets.intelligence import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


def resolve_broll_layers(project: dict[str, Any], project_root: Path) -> dict[str, Any]:
    assets = project.get("assets", {})
    if not isinstance(assets, dict):
        return project
    candidates = _candidate_assets(assets, project_root)
    if not candidates:
        _replace_unresolved_with_text(project)
        return project

    used: set[str] = set()
    for scene in project.get("timeline", []):
        if not isinstance(scene, dict):
            continue
        for layer in scene.get("layers", []):
            if not isinstance(layer, dict) or str(layer.get("type")) not in {"broll", "b-roll"}:
                continue
            query = str(layer.get("query") or layer.get("text") or scene.get("id", ""))
            chosen = _best_candidate(query, candidates, used)
            if not chosen:
                layer.clear()
                layer.update(_fallback_text_layer(query))
                continue
            used.add(chosen["key"])
            layer["type"] = chosen["type"]
            layer["asset"] = chosen["key"]
            layer.setdefault("layout", "center")
            layer.setdefault("autoFit", "cover" if chosen["type"] == "video" else "contain")
            layer.setdefault("animation", {"in": "fade", "out": "fade", "duration": 0.25})
            layer.setdefault("metadata", {})["resolvedFromBroll"] = query
    return project


def _candidate_assets(assets: dict[str, Any], project_root: Path) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for key, raw_value in assets.items():
        value = str(raw_value)
        path = Path(value) if Path(value).is_absolute() else project_root / value
        if path.is_dir():
            for item in path.rglob("*"):
                _append_candidate(candidates, str(key), item)
        else:
            _append_candidate(candidates, str(key), path)
    return candidates


def _append_candidate(candidates: list[dict[str, str]], key: str, path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        candidates.append({"key": key, "path": str(path), "type": "video", "name": f"{key} {path.stem}".lower()})
    elif suffix in IMAGE_EXTENSIONS:
        candidates.append({"key": key, "path": str(path), "type": "image", "name": f"{key} {path.stem}".lower()})


def _best_candidate(query: str, candidates: list[dict[str, str]], used: set[str]) -> dict[str, str] | None:
    terms = {term for term in query.lower().replace("_", " ").split() if len(term) > 2}
    ranked = []
    for candidate in candidates:
        score = 0 if candidate["key"] in used else 1
        score += sum(2 for term in terms if term in candidate["name"])
        if candidate["type"] == "video":
            score += 1
        ranked.append((score, candidate))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked else None


def _replace_unresolved_with_text(project: dict[str, Any]) -> None:
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            if isinstance(layer, dict) and str(layer.get("type")) in {"broll", "b-roll"}:
                layer.clear()
                layer.update(_fallback_text_layer("B-roll needed"))


def _fallback_text_layer(query: str) -> dict[str, Any]:
    return {
        "type": "text",
        "text": f"B-roll: {query}",
        "layout": "lower_third",
        "fontSize": 42,
        "color": "#ffffff",
        "strokeColor": "#000000",
        "strokeWidth": 2,
    }
