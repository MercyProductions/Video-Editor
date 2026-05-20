from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def default_local_policy_path() -> Path:
    return Path(__file__).resolve().parents[2] / "output" / "ecosystem" / "local_first_policy.json"


def init_local_policy(path: Path | None = None) -> dict[str, Any]:
    target = path or default_local_policy_path()
    policy = {
        "format": "automatic-video-editor-local-first-policy",
        "version": 1,
        "localFirst": True,
        "offlineCapable": True,
        "telemetryEnabled": False,
        "accountsRequired": False,
        "networkFeatures": {
            "cloudSync": False,
            "cloudRendering": False,
            "remoteRenderWorkers": False,
            "remoteBackups": False,
            "onlineCollaboration": False,
            "marketplaceServers": False,
        },
        "localSystems": {
            "assetDatabase": "sqlite",
            "reviewNotes": "project sidecar json",
            "renderWorkers": "same-machine subprocess",
            "packs": "file-based zip packages",
            "plugins": "local folders only",
            "analytics": "local jsonl metrics only",
        },
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    policy["path"] = str(target.resolve())
    return policy


def load_local_policy(path: Path | None = None) -> dict[str, Any]:
    target = path or default_local_policy_path()
    if not target.exists():
        return init_local_policy(target)
    data = json.loads(target.read_text(encoding="utf-8"))
    data["path"] = str(target.resolve())
    return data
