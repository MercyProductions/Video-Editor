from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any


def export_training_dataset(project_paths: list[Path], output_path: Path, *, include_text: bool = False) -> dict[str, Any]:
    rows = []
    for path in project_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append(_project_row(path, data, include_text=include_text))
    dataset = {
        "format": "automatic-video-editor-local-training-dataset",
        "version": 1,
        "createdAt": _now(),
        "privacy": {
            "localOnly": True,
            "anonymized": not include_text,
            "includesSourcePaths": False,
            "includesScriptText": include_text,
        },
        "projectCount": len(rows),
        "projects": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")
    return {**dataset, "path": str(output_path.resolve())}


def _project_row(path: Path, data: dict[str, Any], *, include_text: bool) -> dict[str, Any]:
    timeline = data.get("timeline", [])
    transitions = Counter()
    layer_types = Counter()
    effects = Counter()
    caption_words = 0
    scenes = []
    for scene in timeline:
        transition = scene.get("transitionOut")
        if isinstance(transition, dict):
            transitions[str(transition.get("type", "cut"))] += 1
        scene_layers = []
        for layer in scene.get("layers", []):
            kind = str(layer.get("type", "unknown"))
            layer_types[kind] += 1
            animation = layer.get("animation")
            if isinstance(animation, dict):
                for value in animation.values():
                    if isinstance(value, str):
                        effects[value] += 1
            raw_effects = layer.get("effects")
            if isinstance(raw_effects, str):
                effects[raw_effects] += 1
            elif isinstance(raw_effects, list):
                effects.update(str(item) for item in raw_effects)
            if kind in {"caption", "captions"}:
                caption_words += _caption_words(layer)
            scene_layers.append({"type": kind, "duration": layer.get("duration"), "hasAsset": bool(layer.get("asset")), **({"text": layer.get("text")} if include_text and layer.get("text") else {})})
        scenes.append({"idHash": _hash(str(scene.get("id", ""))), "start": scene.get("start"), "duration": scene.get("duration"), "layerTypes": scene_layers})
    duration = float(data.get("project", {}).get("duration", 0) or 0)
    return {
        "projectId": _hash(str(path.resolve())),
        "stylePreset": data.get("stylePreset") or data.get("metadata", {}).get("stylePreset"),
        "exportPreset": data.get("exportPreset"),
        "duration": duration,
        "sceneCount": len(timeline),
        "transitionUsage": dict(transitions),
        "layerUsage": dict(layer_types),
        "effectUsage": dict(effects),
        "captionWordsPerSecond": round(caption_words / max(duration, 0.001), 3),
        "timingPattern": [round(float(scene.get("duration", 0) or 0), 3) for scene in timeline],
        "scenes": scenes,
    }


def _caption_words(layer: dict[str, Any]) -> int:
    if layer.get("items"):
        return sum(len(str(item.get("text", "")).split()) for item in layer.get("items", []))
    return len(str(layer.get("text", "")).split())


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
