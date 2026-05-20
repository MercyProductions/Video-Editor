from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


@dataclass(slots=True)
class ProjectSettings:
    width: int
    height: int
    fps: int
    duration: float
    background: str = "#000000"
    export_preset: str | None = None
    crf: int = 18


@dataclass(slots=True)
class Layer:
    type: str
    raw: JsonDict

    @property
    def start(self) -> float:
        return float(self.raw.get("start", 0))

    def duration(self, scene_duration: float) -> float:
        value = self.raw.get("duration")
        if value is None:
            return max(scene_duration - self.start, 0)
        return float(value)


@dataclass(slots=True)
class Scene:
    id: str
    start: float
    duration: float
    layers: list[Layer]
    transition_out: JsonDict | None = None
    raw: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class AudioTrack:
    asset: str
    start: float
    raw: JsonDict


@dataclass(slots=True)
class ProjectConfig:
    path: Path
    root_dir: Path
    settings: ProjectSettings
    assets: dict[str, str]
    timeline: list[Scene]
    audio: list[AudioTrack]
    captions: list[JsonDict]
    metadata: JsonDict
    export_preset: str | None
    raw: JsonDict

    @property
    def output_dir(self) -> Path:
        return self.path.parent / "output"
