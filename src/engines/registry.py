from __future__ import annotations

from typing import Any


def engine_registry() -> dict[str, Any]:
    """Describe the current modular engine split using real package boundaries."""
    return {
        "renderEngine": {
            "modules": ["renderer.renderer", "renderer.ffmpeg", "renderer.reliability", "effects.video", "effects.text", "effects.graphics", "effects.graph", "transitions.transitions"],
            "responsibility": "FFmpeg scene rendering, transitions, audio mixing, render reports, cache-aware rendering.",
        },
        "timelineEngine": {
            "modules": ["parser.project_parser", "parser.models", "layout.smart_layout", "preview.reporter", "preview.realtime"],
            "responsibility": "JSON validation, timeline normalization, smart layout, preview plans.",
        },
        "aiEngine": {
            "modules": ["local_ai.engine", "local_ai.model_manager", "ai.generator", "ai.director", "content.pipeline", "content.scene_builder", "content.suggestions", "showcase.analyzer", "showcase.builder", "showcase.styles", "intelligence.beat_sync", "intelligence.clip_understanding"],
            "responsibility": "Local prompt interpretation, local model integration points, scene suggestions, beat sync, media understanding, content workflows.",
        },
        "assetEngine": {
            "modules": ["assets.resolver", "assets.intelligence", "assets.database", "broll.resolver", "recovery.integrity"],
            "responsibility": "Asset resolving, indexing, SQLite metadata, usage tracking, B-roll resolution.",
        },
        "pluginEngine": {
            "modules": ["plugins.registry", "packs.portable_pack"],
            "responsibility": "Local plugin manifests, permission audits, and offline pack import/export.",
        },
        "uiLayer": {
            "modules": ["desktop-app/electron", "desktop-app/src"],
            "responsibility": "Electron/React UI over the JSON source of truth.",
        },
        "exportEngine": {
            "modules": ["presets.export_presets", "project_packaging.project_package", "social.reformat", "reports.render_report", "workers.local_render", "installer.local_installer"],
            "responsibility": "Export presets, package portability, social variants, reports, same-machine render queue workers.",
        },
        "qualityEngine": {
            "modules": ["quality.checker", "feedback.loops", "evolution.report", "refinement.polish", "color.pipeline", "stability.dependencies", "stability.performance", "stability.cache", "finalization.audit", "finalization.profiler", "finalization.release"],
            "responsibility": "Preflight quality checks, feedback learning, long-term evolution reports, cinematic refinement, profiling, diagnostics, and release readiness.",
        },
    }


def api_surface() -> dict[str, Any]:
    registry = engine_registry()
    return {
        "format": "automatic-video-editor-local-api",
        "version": 1,
        "localFirst": True,
        "engines": registry,
        "stableCommands": [
            "render",
            "validate",
            "preview",
            "pipeline",
            "showcase",
            "cinematic-enhance",
            "workspace",
            "review",
            "asset-db",
            "pack",
            "dataset-export",
            "analytics",
            "local-policy",
            "diagnostics",
            "worker",
            "local-ai",
            "model-manager",
            "dependency-check",
            "privacy-report",
            "performance-report",
            "refine",
            "color",
            "cache",
            "workflow",
            "feedback",
            "evolution-report",
            "release-check",
        ],
    }
