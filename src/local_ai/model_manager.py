from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


LOCAL_TASKS = {
    "prompt_to_json",
    "json_repair",
    "scene_suggestions",
    "captions",
    "transcription",
}

MODEL_FILE_EXTENSIONS = {".gguf", ".bin", ".safetensors", ".pt", ".pth", ".onnx"}


def model_manager_status(*, output_path: Path | None = None, registry_path: Path | None = None) -> dict[str, Any]:
    """Return a local-only model inventory and health report."""
    registry = load_model_registry(registry_path)
    ollama = detect_ollama()
    whisper = detect_whisper_tools()
    files = detect_model_files()
    report = {
        "format": "automatic-video-editor-local-model-status",
        "createdAt": _now(),
        "privacy": {
            "localOnly": True,
            "apiKeysRequired": False,
            "networkPolicy": "localhost endpoints only",
            "telemetry": False,
        },
        "registryPath": str((registry_path or default_model_registry_path()).resolve()),
        "selections": registry.get("selections", {}),
        "tasks": {task: select_model_for_task(task, registry=registry, ollama=ollama, whisper=whisper, files=files) for task in sorted(LOCAL_TASKS)},
        "ollama": ollama,
        "whisper": whisper,
        "modelFiles": files,
        "warnings": _warnings(ollama, whisper, files),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def default_model_registry_path() -> Path:
    return Path(__file__).resolve().parents[2] / "output" / "local_models" / "model_registry.json"


def load_model_registry(path: Path | None = None) -> dict[str, Any]:
    path = path or default_model_registry_path()
    if not path.exists():
        return {"version": 1, "selections": {}, "fallbackPolicy": "use heuristic generator when no local model is healthy"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "selections": {}, "fallbackPolicy": "registry was unreadable; using safe defaults"}


def save_model_selection(task: str, model: str, *, registry_path: Path | None = None) -> dict[str, Any]:
    if task not in LOCAL_TASKS:
        raise ValueError(f"Unknown model task '{task}'. Expected one of: {', '.join(sorted(LOCAL_TASKS))}")
    path = registry_path or default_model_registry_path()
    registry = load_model_registry(path)
    registry.setdefault("version", 1)
    registry.setdefault("selections", {})[task] = {"model": model, "updatedAt": _now()}
    registry.setdefault("fallbackPolicy", "use heuristic generator when no local model is healthy")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    return registry


def detect_ollama(endpoint: str | None = None, *, timeout: float = 2.5) -> dict[str, Any]:
    endpoint = (endpoint or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
    executable = shutil.which("ollama")
    cli_models = _ollama_cli_models(executable)
    endpoint_models, endpoint_ok, endpoint_error = _ollama_endpoint_models(endpoint, timeout=timeout)
    models = endpoint_models or cli_models
    return {
        "installed": bool(executable),
        "executable": executable,
        "endpoint": endpoint,
        "endpointHealthy": endpoint_ok,
        "endpointError": endpoint_error,
        "models": models,
        "modelCount": len(models),
        "health": "healthy" if endpoint_ok and models else "available" if executable or models else "missing",
    }


def detect_whisper_tools() -> dict[str, Any]:
    tools = []
    for name in ("whisper", "faster-whisper", "whisperx"):
        executable = shutil.which(name)
        tools.append({"name": name, "available": bool(executable), "executable": executable})
    return {
        "tools": tools,
        "available": any(tool["available"] for tool in tools),
        "preferred": next((tool for tool in tools if tool["available"]), None),
    }


def detect_model_files(model_roots: list[Path] | None = None, *, limit: int = 250) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    roots = model_roots or [
        root / "models",
        root / "output" / "models",
        Path.home() / ".ollama" / "models",
        Path.home() / ".cache" / "huggingface",
    ]
    models: list[dict[str, Any]] = []
    for folder in roots:
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if len(models) >= limit:
                break
            if path.is_file() and path.suffix.lower() in MODEL_FILE_EXTENSIONS:
                stat = path.stat()
                models.append(
                    {
                        "name": path.stem,
                        "path": str(path.resolve()),
                        "extension": path.suffix.lower(),
                        "bytes": stat.st_size,
                        "modifiedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime)),
                    }
                )
    return {"roots": [str(path.resolve()) for path in roots], "models": models, "modelCount": len(models), "truncated": len(models) >= limit}


def select_model_for_task(
    task: str,
    *,
    registry: dict[str, Any] | None = None,
    ollama: dict[str, Any] | None = None,
    whisper: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if task not in LOCAL_TASKS:
        raise ValueError(f"Unknown model task '{task}'.")
    registry = registry or load_model_registry()
    ollama = ollama or detect_ollama()
    whisper = whisper or detect_whisper_tools()
    files = files or detect_model_files()
    selected = registry.get("selections", {}).get(task, {})
    if selected.get("model"):
        return {"task": task, "selected": selected["model"], "source": "registry", "available": True}
    if task == "transcription":
        preferred = whisper.get("preferred")
        if preferred:
            return {"task": task, "selected": preferred["name"], "source": "local-whisper-cli", "available": True}
        return {"task": task, "selected": "transcript-file-fallback", "source": "fallback", "available": False}
    models = ollama.get("models", [])
    if models:
        return {"task": task, "selected": models[0].get("name", "ollama-local-model"), "source": "ollama", "available": bool(ollama.get("endpointHealthy"))}
    file_models = files.get("models", [])
    if file_models:
        return {"task": task, "selected": file_models[0]["name"], "source": "local-model-file", "available": True}
    return {"task": task, "selected": "heuristic-local-engine", "source": "fallback", "available": False}


def _ollama_cli_models(executable: str | None) -> list[dict[str, Any]]:
    if not executable:
        return []
    try:
        result = subprocess.run([executable, "list"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    except Exception:
        return []
    if result.returncode != 0:
        return []
    rows = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        rows.append({"name": parts[0], "source": "ollama-cli"})
    return rows


def _ollama_endpoint_models(endpoint: str, *, timeout: float) -> tuple[list[dict[str, Any]], bool, str | None]:
    try:
        request = Request(f"{endpoint}/api/tags", headers={"User-Agent": "automatic-video-editor-local"})
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = [{"name": item.get("name", "unknown"), "size": item.get("size"), "source": "ollama-endpoint"} for item in data.get("models", [])]
        return models, True, None
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return [], False, str(exc)


def _warnings(ollama: dict[str, Any], whisper: dict[str, Any], files: dict[str, Any]) -> list[str]:
    warnings = []
    if not ollama.get("installed") and not ollama.get("endpointHealthy"):
        warnings.append("No local LLM endpoint detected. Prompt-to-JSON will use deterministic heuristic generation.")
    if not whisper.get("available"):
        warnings.append("No local Whisper CLI detected. Auto transcription needs transcript files or a local Whisper install.")
    if not files.get("modelCount") and not ollama.get("modelCount"):
        warnings.append("No local model files were found in the configured model folders.")
    return warnings


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
