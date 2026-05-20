from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


def default_queue_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "output" / "render_workers" / "queue"


def enqueue_render(project_path: Path, *, output_path: Path | None = None, queue_dir: Path | None = None, quality: str = "preview") -> dict[str, Any]:
    queue_dir = queue_dir or default_queue_dir()
    queue_dir.mkdir(parents=True, exist_ok=True)
    job_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "_" + uuid.uuid4().hex[:8]
    job = {
        "id": job_id,
        "project": str(project_path.resolve()),
        "output": str(output_path.resolve()) if output_path else str((queue_dir.parent / "renders" / f"{project_path.stem}.{job_id}.mp4").resolve()),
        "quality": quality,
        "status": "queued",
        "createdAt": _now(),
        "attempts": 0,
        "localOnly": True,
    }
    _write(queue_dir / f"{job_id}.job.json", job)
    return job


def run_worker(queue_dir: Path | None = None, *, once: bool = True, timeout_seconds: float = 1800) -> dict[str, Any]:
    queue_dir = queue_dir or default_queue_dir()
    queue_dir.mkdir(parents=True, exist_ok=True)
    worker_dir = queue_dir.parent
    worker_dir.mkdir(parents=True, exist_ok=True)
    heartbeat_path = worker_dir / "worker_heartbeat.json"
    processed = []
    while True:
        job_path = _next_job(queue_dir)
        if not job_path:
            break
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["status"] = "running"
        job["startedAt"] = _now()
        job["attempts"] = int(job.get("attempts", 0)) + 1
        _write(job_path, job)
        _write(heartbeat_path, {"status": "running", "job": job["id"], "updatedAt": _now()})
        result = _run_job(job, timeout_seconds=timeout_seconds)
        job.update(result)
        job["finishedAt"] = _now()
        _write(job_path, job)
        processed.append(job)
        _write(heartbeat_path, {"status": "idle", "lastJob": job["id"], "updatedAt": _now()})
        if once:
            break
    report = {"queue": str(queue_dir.resolve()), "processed": len(processed), "jobs": processed, "heartbeat": str(heartbeat_path.resolve())}
    _write(queue_dir.parent / "worker_report.json", report)
    return report


def worker_status(queue_dir: Path | None = None) -> dict[str, Any]:
    queue_dir = queue_dir or default_queue_dir()
    jobs = []
    for path in sorted(queue_dir.glob("*.job.json")) if queue_dir.exists() else []:
        try:
            jobs.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            jobs.append({"path": str(path), "status": "corrupt"})
    heartbeat = queue_dir.parent / "worker_heartbeat.json"
    return {
        "queue": str(queue_dir.resolve()),
        "queued": sum(1 for job in jobs if job.get("status") == "queued"),
        "running": sum(1 for job in jobs if job.get("status") == "running"),
        "failed": sum(1 for job in jobs if job.get("status") == "failed"),
        "completed": sum(1 for job in jobs if job.get("status") == "completed"),
        "jobs": jobs,
        "heartbeat": json.loads(heartbeat.read_text(encoding="utf-8")) if heartbeat.exists() else None,
    }


def _run_job(job: dict[str, Any], *, timeout_seconds: float) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    render_py = root / "render.py"
    output = Path(job["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    log_path = output.with_suffix(".worker.log")
    sandbox_dir = output.parent / f".sandbox_{job['id']}"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(render_py), "render", job["project"], "-o", str(output), "--quality", job.get("quality", "preview"), "--cache", "--resume"]
    started = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout_seconds)
        log_path.write_text(result.stdout or "", encoding="utf-8")
        ok = result.returncode == 0 and output.exists()
        return {
            "status": "completed" if ok else "failed",
            "returnCode": result.returncode,
            "renderSeconds": round(time.perf_counter() - started, 3),
            "log": str(log_path.resolve()),
            "sandbox": str(sandbox_dir.resolve()),
            "outputExists": output.exists(),
        }
    except subprocess.TimeoutExpired as exc:
        log_path.write_text(str(exc), encoding="utf-8")
        return {
            "status": "failed",
            "returnCode": None,
            "renderSeconds": round(time.perf_counter() - started, 3),
            "log": str(log_path.resolve()),
            "sandbox": str(sandbox_dir.resolve()),
            "watchdog": f"Timed out after {timeout_seconds}s",
        }


def _next_job(queue_dir: Path) -> Path | None:
    for path in sorted(queue_dir.glob("*.job.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("status") in {"queued", "failed"}:
            return path
    return None


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
