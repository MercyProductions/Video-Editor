from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PLUGIN_TYPES = {"transition", "effect", "template", "export_preset", "automation"}
PERMISSIONS = {"read_project", "write_project", "read_assets", "write_assets", "run_ffmpeg", "spawn_process"}


def list_plugins(root: Path | None = None) -> list[dict[str, Any]]:
    root = root or Path(__file__).resolve().parents[2] / "plugins"
    if not root.exists():
        return []
    plugins = []
    for manifest_path in root.glob("*/plugin.json"):
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        manifest["path"] = str(manifest_path.parent.resolve())
        manifest.setdefault("enabled", not manifest.get("disabled", False))
        plugins.append(manifest)
    return sorted(plugins, key=lambda item: (item.get("type", ""), item.get("name", "")))


def init_plugin(name: str, plugin_type: str, root: Path | None = None) -> dict[str, Any]:
    if plugin_type not in PLUGIN_TYPES:
        raise ValueError(f"Unsupported plugin type '{plugin_type}'. Expected one of: {', '.join(sorted(PLUGIN_TYPES))}")
    root = root or Path(__file__).resolve().parents[2] / "plugins"
    plugin_dir = root / _slug(name)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": name,
        "id": _slug(name),
        "type": plugin_type,
        "version": "0.1.0",
        "description": f"Custom {plugin_type.replace('_', ' ')} plugin.",
        "entry": "plugin.json",
        "localOnly": True,
        "enabled": True,
        "sandbox": {"mode": "manifest_only", "crashIsolation": True},
        "permissions": [],
        "capabilities": _default_capabilities(plugin_type),
    }
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    readme = plugin_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {name}\n\n"
            "This plugin manifest is discovered by `python render.py plugin list`.\n"
            "Future engine hooks can load transitions, effects, templates, and export presets from this folder.\n",
            encoding="utf-8",
        )
    manifest["path"] = str(plugin_dir.resolve())
    return manifest


def audit_plugins(root: Path | None = None) -> dict[str, Any]:
    plugins = list_plugins(root)
    warnings = []
    for plugin in plugins:
        permissions = set(plugin.get("permissions", []))
        unknown = sorted(permissions - PERMISSIONS)
        risky = sorted(permissions & {"write_project", "write_assets", "spawn_process"})
        if not plugin.get("localOnly", True):
            warnings.append({"plugin": plugin.get("id"), "severity": "error", "message": "Plugin must be local-only."})
        if unknown:
            warnings.append({"plugin": plugin.get("id"), "severity": "error", "message": f"Unknown permissions: {', '.join(unknown)}"})
        if risky:
            warnings.append({"plugin": plugin.get("id"), "severity": "warning", "message": f"Requires confirmation for: {', '.join(risky)}"})
        if plugin.get("disabled"):
            warnings.append({"plugin": plugin.get("id"), "severity": "info", "message": "Plugin is disabled and will not be loaded."})
        if not plugin.get("sandbox"):
            warnings.append({"plugin": plugin.get("id"), "severity": "warning", "message": "Plugin manifest does not declare sandbox metadata."})
        if Path(plugin.get("path", "")).is_absolute() and "plugins" not in Path(plugin["path"]).parts:
            warnings.append({"plugin": plugin.get("id"), "severity": "warning", "message": "Plugin is outside the local plugins folder."})
    return {
        "pluginCount": len(plugins),
        "plugins": plugins,
        "allowedPermissions": sorted(PERMISSIONS),
        "warnings": warnings,
        "isolation": "manifest-only by default; executable hooks must request permissions and run as separate local processes",
    }


def set_plugin_enabled(plugin_id: str, enabled: bool, root: Path | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[2] / "plugins"
    for manifest_path in root.glob("*/plugin.json"):
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        if manifest.get("id") != plugin_id:
            continue
        manifest["enabled"] = enabled
        manifest["disabled"] = not enabled
        manifest.setdefault("sandbox", {"mode": "manifest_only", "crashIsolation": True})
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        manifest["path"] = str(manifest_path.parent.resolve())
        return manifest
    raise FileNotFoundError(f"Plugin '{plugin_id}' was not found in {root}")


def _default_capabilities(plugin_type: str) -> dict[str, Any]:
    if plugin_type == "transition":
        return {"transitions": []}
    if plugin_type == "effect":
        return {"effects": []}
    if plugin_type == "template":
        return {"templates": []}
    if plugin_type == "automation":
        return {"automationScripts": []}
    return {"exportPresets": []}


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "plugin"
