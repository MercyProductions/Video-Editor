from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ai.generator import generate_project_from_prompt
from captions.engine import add_captions_from_transcript
from content.suggestions import suggest_scene_improvements
from local_ai.model_manager import model_manager_status
from repair.repairer import repair_project_file


def local_ai_status() -> dict[str, Any]:
    manager = model_manager_status()
    return {
        "localOnly": True,
        "apiKeysRequired": False,
        "integrations": {
            "ollama": {
                "available": bool(shutil.which("ollama")) or bool(manager.get("ollama", {}).get("endpointHealthy")),
                "command": shutil.which("ollama"),
                "endpointHealthy": manager.get("ollama", {}).get("endpointHealthy"),
                "modelCount": manager.get("ollama", {}).get("modelCount"),
            },
            "whisperCli": {"available": bool(shutil.which("whisper")), "command": shutil.which("whisper")},
        },
        "modelRouting": manager.get("tasks", {}),
        "warnings": manager.get("warnings", []),
        "builtIn": {
            "promptToJson": True,
            "jsonRepair": True,
            "captionFromTranscript": True,
            "sceneSuggestions": True,
        },
    }


def local_prompt_to_json(prompt: str, *, output_path: Path, template: str | None = None, preset: str | None = None) -> dict[str, Any]:
    project = generate_project_from_prompt(prompt, template=template, preset=preset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    return {"output": str(output_path.resolve()), "project": project}


def local_repair(project_path: Path, *, output_path: Path) -> dict[str, Any]:
    result = repair_project_file(project_path, output_path)
    return {"output": str(output_path.resolve()), "valid": result.valid, "fixes": result.fixes, "errorsBefore": result.errors_before, "errorsAfter": result.errors_after}


def local_scene_suggestions(project_path: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    project = json.loads(project_path.read_text(encoding="utf-8"))
    result = suggest_scene_improvements(project)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def local_caption_from_transcript(project_path: Path, transcript_path: Path, *, output_path: Path, mode: str = "smart", style: str = "tiktok") -> dict[str, Any]:
    project = json.loads(project_path.read_text(encoding="utf-8"))
    add_captions_from_transcript(project, transcript_path, mode=mode, style=style)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    return {"output": str(output_path.resolve()), "captionCount": len(project.get("captions", []))}


def local_transcribe(audio_path: Path, *, output_path: Path) -> dict[str, Any]:
    whisper = shutil.which("whisper")
    if not whisper:
        return {"available": False, "error": "Local whisper CLI not found on PATH.", "output": str(output_path.resolve())}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [whisper, str(audio_path.resolve()), "--output_format", "srt", "--output_dir", str(output_path.parent.resolve())],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {"available": True, "returnCode": result.returncode, "log": result.stdout, "outputDir": str(output_path.parent.resolve())}
