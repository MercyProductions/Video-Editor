from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from ai.generator import generate_project_from_prompt
from captions.engine import add_captions_from_transcript
from content.suggestions import suggest_scene_improvements
from local_ai.model_manager import model_manager_status
from repair.repairer import repair_project_data, repair_project_file
from schema.validator import ProjectValidationError, validate_project


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
    warnings: list[str] = []
    model_result = _try_ollama_prompt_to_json(prompt, template=template, preset=preset)
    if model_result:
        project = model_result["project"]
        source = model_result["source"]
        model = model_result.get("model")
        warnings.extend(model_result.get("warnings", []))
    else:
        project = generate_project_from_prompt(prompt, template=template, preset=preset)
        source = "heuristic-local-engine"
        model = None

    project, validation_report = _validate_or_repair_generated_project(project)
    warnings.extend(validation_report.get("warnings", []))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    return {
        "output": str(output_path.resolve()),
        "project": project,
        "source": source,
        "model": model,
        "validation": validation_report,
        "warnings": warnings,
    }


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


def _try_ollama_prompt_to_json(prompt: str, *, template: str | None, preset: str | None) -> dict[str, Any] | None:
    manager = model_manager_status()
    task = manager.get("tasks", {}).get("prompt_to_json", {})
    if task.get("source") != "ollama" or not task.get("available") or not task.get("selected"):
        return None

    endpoint = str(manager.get("ollama", {}).get("endpoint") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
    model = str(task["selected"])
    body = {
        "model": model,
        "prompt": _prompt_to_project_json_instruction(prompt, template=template, preset=preset),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.15, "top_p": 0.9},
    }
    request = Request(
        f"{endpoint}/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "automatic-video-editor-local"},
    )
    try:
        timeout = float(os.environ.get("AVE_OLLAMA_TIMEOUT", "45"))
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        generated = _extract_json_object(str(payload.get("response", "")))
        if not generated:
            return None
        generated.setdefault("metadata", {})
        generated["metadata"]["localAi"] = {
            "source": "ollama",
            "model": model,
            "endpoint": endpoint,
            "task": "prompt_to_json",
        }
        return {"project": generated, "source": "ollama", "model": model, "warnings": []}
    except (OSError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def _prompt_to_project_json_instruction(prompt: str, *, template: str | None, preset: str | None) -> str:
    return f"""
You are the local prompt-to-JSON planner for Automatic Video Editor.
Return only one valid JSON object. No markdown.

Required top-level shape:
{{
  "project": {{"width": 1920, "height": 1080, "fps": 60, "duration": 12, "background": "#000000"}},
  "assets": {{}},
  "timeline": [
    {{"id": "scene_1", "start": 0, "duration": 4, "layers": [
      {{"type": "text", "text": "Title", "x": "center", "y": "center", "fontSize": 72, "color": "#ffffff"}}
    ], "transitionOut": {{"type": "crossfade", "duration": 0.5}}}}
  ],
  "audio": [],
  "metadata": {{"contentSummary": "..."}}
}}

Rules:
- JSON must validate against the app schema.
- Use only local asset placeholders or empty assets when no file paths are provided.
- Keep scene timings continuous and inside project.duration.
- Prefer text/title-card plans if no usable assets are provided.
- Template hint: {template or "none"}.
- Export preset hint: {preset or "none"}.

User prompt:
{prompt}
""".strip()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    value = json.loads(text[start : end + 1])
    return value if isinstance(value, dict) else None


def _validate_or_repair_generated_project(project: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        validate_project(project)
        return project, {"valid": True, "repaired": False, "warnings": []}
    except ProjectValidationError as exc:
        repaired = repair_project_data(project)
        if repaired.valid:
            return repaired.data, {"valid": True, "repaired": True, "fixes": repaired.fixes, "warnings": ["Generated JSON was repaired before saving."]}
        return (
            repaired.data,
            {
                "valid": False,
                "repaired": True,
                "fixes": repaired.fixes,
                "errorsBefore": str(exc).splitlines(),
                "errorsAfter": repaired.errors_after,
                "warnings": ["Generated JSON still has validation issues after repair."],
            },
        )
