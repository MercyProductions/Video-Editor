from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from local_ai.model_manager import model_manager_status
from plugins.registry import audit_plugins


def privacy_security_report(*, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    plugin_audit = audit_plugins()
    local_ai = model_manager_status()
    report = {
        "format": "automatic-video-editor-privacy-security-report",
        "createdAt": _now(),
        "privacy": {
            "localFirst": True,
            "telemetry": False,
            "accountsRequired": False,
            "cloudRendering": False,
            "cloudSync": False,
            "remoteBackups": False,
            "requiredApiKeys": False,
        },
        "localPaths": {
            "projectRoot": str(root.resolve()),
            "output": str((root / "output").resolve()),
            "plugins": str((root / "plugins").resolve()),
            "models": str((root / "models").resolve()),
        },
        "localAi": {
            "networkPolicy": local_ai["privacy"]["networkPolicy"],
            "tasks": local_ai["tasks"],
            "warnings": local_ai["warnings"],
        },
        "plugins": {
            "pluginCount": plugin_audit["pluginCount"],
            "allowedPermissions": plugin_audit["allowedPermissions"],
            "warnings": plugin_audit["warnings"],
            "isolation": plugin_audit["isolation"],
        },
        "safeDefaults": [
            "Plugins are manifest-only until explicitly loaded by local commands.",
            "Local AI uses localhost endpoints or deterministic fallback generation.",
            "Project packages are local zip files.",
            "Analytics are stored only under the local output folder.",
        ],
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
