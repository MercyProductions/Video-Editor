from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from broll.resolver import resolve_broll_layers
from layout.smart_layout import apply_smart_layout
from parser.models import AudioTrack, Layer, ProjectConfig, ProjectSettings, Scene
from presets.export_presets import apply_export_preset
from schema.validator import validate_project
from styles.presets import apply_style


class ProjectParser:
    def load(self, path: Path) -> ProjectConfig:
        logging.info("Loading project file: %s", path)
        if not path.exists():
            raise FileNotFoundError(f"Project file not found: {path}")

        with path.open("r", encoding="utf-8") as handle:
            data: dict[str, Any] = json.load(handle)

        logging.info("Validating JSON schema")
        validate_project(data)
        data = resolve_broll_layers(data, path.parent)
        if data.get("stylePreset"):
            data = apply_style(data, str(data["stylePreset"]))
        self._attach_global_captions(data)
        data = apply_smart_layout(data)

        project = apply_export_preset(data["project"], data.get("exportPreset"))
        settings = ProjectSettings(
            width=int(project["width"]),
            height=int(project["height"]),
            fps=int(project["fps"]),
            duration=float(project["duration"]),
            background=project.get("background", "#000000"),
            export_preset=project.get("exportPreset") or data.get("exportPreset"),
            crf=int(project.get("crf", 18)),
        )

        renderable_scenes = [
            scene for scene in data.get("timeline", [])
            if not scene.get("excludeFromFinal") and scene.get("enabled", True) is not False
        ]
        timeline = [
            Scene(
                id=str(scene["id"]),
                start=float(scene["start"]),
                duration=float(scene["duration"]),
                layers=[Layer(type=str(layer["type"]), raw=layer) for layer in scene.get("layers", [])],
                transition_out=scene.get("transitionOut"),
                raw=scene,
            )
            for scene in renderable_scenes
        ]
        timeline.sort(key=lambda scene: scene.start)

        audio = [
            AudioTrack(asset=str(track["asset"]), start=float(track.get("start", 0)), raw=track)
            for track in data.get("audio", [])
        ]

        config = ProjectConfig(
            path=path,
            root_dir=path.parent,
            settings=settings,
            assets=data.get("assets", {}),
            timeline=timeline,
            audio=audio,
            captions=data.get("captions", []),
            metadata=data.get("metadata", {}),
            export_preset=data.get("exportPreset") or project.get("exportPreset"),
            raw=data,
        )
        logging.info("Building timeline: %d scenes, %d audio tracks", len(timeline), len(audio))
        return config

    def _attach_global_captions(self, data: dict[str, Any]) -> None:
        captions = data.get("captions")
        timeline = data.get("timeline")
        if not captions or not isinstance(timeline, list):
            return
        has_caption_layer = any(
            layer.get("type") in {"caption", "captions"}
            for scene in timeline
            for layer in scene.get("layers", [])
            if isinstance(layer, dict)
        )
        if has_caption_layer:
            return
        target = max(timeline, key=lambda scene: float(scene.get("duration", 0)))
        target.setdefault("layers", []).append(
            {
                "type": "caption",
                "layout": "lower_third",
                "fontSize": 44,
                "color": "#ffffff",
                "strokeColor": "#000000",
                "strokeWidth": 3,
                "box": True,
                "boxColor": "#00000099",
                "boxPadding": 14,
                "items": captions,
            }
        )
