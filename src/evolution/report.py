from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from analytics.creator import creator_analytics
from engines.registry import api_surface, engine_registry
from feedback.loops import creator_identity_report, hook_effectiveness_report, render_self_analysis, style_consistency_report
from finalization.audit import architecture_audit
from finalization.release import release_candidate_check
from local_ai.engine import local_ai_status
from quality.checker import run_quality_check
from stability.performance import performance_dashboard_report
from workflow.creator import production_dashboard


def build_evolution_report(
    *,
    project_path: Path | None = None,
    profile_name: str = "Default Creator",
    output_path: Path | None = None,
    include_release_check: bool = False,
) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    project = project_path.resolve() if project_path else None
    architecture = architecture_audit()
    performance = performance_dashboard_report()
    workflow = production_dashboard(project_path=project if project and project.exists() else None)
    analytics = creator_analytics()
    local_ai = local_ai_status()
    identity = creator_identity_report(profile_name)
    project_intelligence = _project_intelligence(project, profile_name) if project and project.exists() else {"available": False}
    report = {
        "format": "automatic-video-editor-long-term-evolution-report",
        "reportVersion": 1,
        "createdAt": _now(),
        "root": str(root.resolve()),
        "localFirst": True,
        "telemetry": False,
        "accountsRequired": False,
        "philosophy": _philosophy(),
        "controlledExpansionGate": _controlled_expansion_gate(),
        "unifiedCreativeWorkspace": _workspace_surface(),
        "engineArchitecture": {
            "registry": engine_registry(),
            "apiSurface": api_surface(),
            "auditSummary": architecture.get("summary", {}),
            "warnings": architecture.get("warnings", []),
            "recommendations": architecture.get("recommendations", []),
        },
        "projectIntelligence": project_intelligence,
        "creatorIdentity": _identity_summary(identity),
        "workflowOptimization": {
            "productionDashboard": _production_summary(workflow),
            "performance": _performance_summary(performance),
            "analytics": analytics,
            "bottlenecks": performance.get("bottlenecks", []),
        },
        "aiCreativeAssistant": _ai_assistant_status(local_ai, identity),
        "maintainability": _maintainability(architecture, workflow, performance),
        "nextActions": _next_actions(architecture, workflow, performance, project_intelligence, identity),
    }
    report["readinessScore"] = _readiness_score(report)
    if include_release_check:
        report["releaseCheck"] = release_candidate_check()
        report["readinessScore"] = min(report["readinessScore"], 90 if report["releaseCheck"].get("ready") else 55)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _project_intelligence(project_path: Path, profile_name: str) -> dict[str, Any]:
    quality = run_quality_check(project_path)
    self_analysis = render_self_analysis(project_path)
    consistency = style_consistency_report(project_path, profile_name=profile_name)
    hook = hook_effectiveness_report(project_path=project_path)
    return {
        "available": True,
        "project": str(project_path),
        "quality": {
            "passed": quality.get("passed"),
            "issueCount": quality.get("issueCount", 0),
            "errorCount": sum(1 for item in quality.get("issues", []) if item.get("severity") == "error"),
            "warningCount": sum(1 for item in quality.get("issues", []) if item.get("severity") == "warning"),
        },
        "pacing": self_analysis.get("pacing", {}),
        "captions": self_analysis.get("captions", {}),
        "motionIntensityScore": self_analysis.get("motionIntensityScore"),
        "styleConsistency": {
            "overallScore": consistency.get("overallScore"),
            "warnings": consistency.get("warnings", []),
        },
        "hookEffectiveness": {
            "retentionPotential": hook.get("scores", {}).get("viewerRetentionPotential"),
            "visualOverloadRisk": hook.get("visualOverloadRisk"),
            "wordCount": hook.get("wordCount"),
        },
        "warnings": self_analysis.get("warnings", [])[:8],
        "recommendations": self_analysis.get("recommendations", [])[:8],
    }


def _philosophy() -> dict[str, Any]:
    return {
        "principles": [
            "local-first",
            "creator-controlled",
            "modular",
            "cinematic",
            "scalable",
            "explainable",
            "deterministic where practical",
        ],
        "priorityOrder": ["stability", "workflow speed", "rendering quality", "AI usefulness", "UX simplicity", "controlled expansion"],
        "sourceOfTruth": "project.json remains the editing backbone.",
    }


def _controlled_expansion_gate() -> dict[str, Any]:
    return {
        "requiredJustifications": [
            "real creator value",
            "workflow improvement",
            "performance cost",
            "memory cost",
            "UI complexity",
            "render complexity",
            "maintenance burden",
            "long-term scalability",
        ],
        "defaultDecision": "Improve an existing workflow before adding a new feature.",
        "doneDefinition": ["compiles", "validates or renders a real workflow", "keeps local-first behavior", "has predictable failure behavior"],
    }


def _workspace_surface() -> dict[str, list[str]]:
    return {
        "editing": ["json editor", "timeline", "preview", "render queue"],
        "assetManagement": ["asset-db", "asset intelligence", "missing asset checks", "project packaging"],
        "aiAssistance": ["content-generate", "youtube-short", "director", "feedback learn", "local-ai"],
        "scriptAndCaptions": ["content plans", "generation review", "captions", "feedback hook analysis"],
        "thumbnailAndPosting": ["thumbnail", "post-package", "reformat"],
        "workflowAutomation": ["workflow profile", "workflow pipeline", "workflow batch", "scheduled local tasks"],
        "creatorMemory": ["feedback reviews", "creator identity", "local training dataset"],
        "maintenance": ["architecture-audit", "release-check", "performance-report", "evolution-report"],
    }


def _identity_summary(identity: dict[str, Any]) -> dict[str, Any]:
    model = identity.get("preferenceModel", {}) if isinstance(identity.get("preferenceModel"), dict) else {}
    return {
        "profile": identity.get("profile"),
        "sampleCount": identity.get("sampleCount", 0),
        "positiveSampleCount": identity.get("positiveSampleCount", 0),
        "preferenceModel": model,
        "generationGuidance": identity.get("generationGuidance", []),
        "path": identity.get("path"),
    }


def _production_summary(workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "recentRenderCount": len(workflow.get("recentRenders", [])),
        "queuedRenders": workflow.get("queuedRenders", 0),
        "runningRenders": workflow.get("runningRenders", 0),
        "renderSuccessRate": workflow.get("renderSuccessRate"),
        "cacheBytes": workflow.get("storage", {}).get("cacheBytes", 0),
        "assetCount": workflow.get("assetDatabase", {}).get("assetCount", 0),
        "duplicateAssetGroups": workflow.get("assetDatabase", {}).get("duplicateGroupCount", 0),
        "workflowHealth": workflow.get("workflowHealth", []),
    }


def _performance_summary(performance: dict[str, Any]) -> dict[str, Any]:
    return {
        "cpu": performance.get("cpu", {}),
        "memory": performance.get("memory", {}),
        "gpu": performance.get("gpu", {}),
        "render": performance.get("render", {}),
        "cache": {
            "bucketCount": performance.get("cache", {}).get("bucketCount", 0),
            "totalBytes": performance.get("cache", {}).get("totalBytes", 0),
        },
        "process": performance.get("process", {}),
    }


def _ai_assistant_status(local_ai: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "roles": ["planner", "editor", "pacing assistant", "showcase director", "workflow helper", "production assistant"],
        "localOnly": local_ai.get("localOnly", True),
        "apiKeysRequired": local_ai.get("apiKeysRequired", False),
        "builtInFallbacks": local_ai.get("builtIn", {}),
        "localIntegrations": local_ai.get("integrations", {}),
        "creatorIdentityAvailable": bool(identity.get("sampleCount")),
        "explainability": identity.get("explainability", ["No creator identity samples recorded yet."]),
        "warnings": local_ai.get("warnings", []),
    }


def _maintainability(architecture: dict[str, Any], workflow: dict[str, Any], performance: dict[str, Any]) -> dict[str, Any]:
    return {
        "architectureWarnings": architecture.get("warnings", []),
        "largeFunctionCount": len(architecture.get("largeFunctions", [])),
        "docCount": architecture.get("summary", {}).get("docCount", 0),
        "pluginWarnings": architecture.get("pluginAudit", {}).get("warnings", []),
        "workflowHealth": workflow.get("workflowHealth", []),
        "performanceBottlenecks": performance.get("bottlenecks", []),
        "debuggability": ["reports are JSON", "project state remains file-based", "release-check validates demos", "feedback artifacts are inspectable"],
    }


def _next_actions(
    architecture: dict[str, Any],
    workflow: dict[str, Any],
    performance: dict[str, Any],
    project_intelligence: dict[str, Any],
    identity: dict[str, Any],
) -> list[str]:
    actions = []
    if architecture.get("warnings"):
        actions.append("Address architecture warnings only where they affect real workflows.")
    if performance.get("bottlenecks"):
        actions.append("Profile and reduce the slowest preview/render/cache bottleneck before expanding UI scope.")
    if workflow.get("workflowHealth"):
        actions.extend(str(item) for item in workflow["workflowHealth"][:2])
    if project_intelligence.get("available") and project_intelligence.get("quality", {}).get("errorCount"):
        actions.append("Fix project quality errors before trusting AI regeneration.")
    if project_intelligence.get("motionIntensityScore", 0) and project_intelligence["motionIntensityScore"] > 85:
        actions.append("Tune motion intensity for readability on the current project.")
    if not identity.get("sampleCount"):
        actions.append("Collect at least one render review so future generations preserve creator identity.")
    if not actions:
        actions.append("Continue refining real workflows; avoid adding new systems until a workflow bottleneck is measured.")
    return actions


def _readiness_score(report: dict[str, Any]) -> int:
    score = 100
    score -= min(25, len(report["engineArchitecture"]["warnings"]) * 6)
    score -= min(20, len(report["workflowOptimization"]["bottlenecks"]) * 5)
    score -= 10 if not report["aiCreativeAssistant"]["creatorIdentityAvailable"] else 0
    project = report.get("projectIntelligence", {})
    if project.get("available"):
        score -= min(20, int(project.get("quality", {}).get("errorCount", 0)) * 10)
        score -= min(12, int(project.get("quality", {}).get("warningCount", 0)) * 2)
        if float(project.get("styleConsistency", {}).get("overallScore") or 100) < 70:
            score -= 8
    return max(0, min(100, score))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
