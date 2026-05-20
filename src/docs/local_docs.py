from __future__ import annotations

from pathlib import Path


DOCS = {
    "json": "JSON_GUIDE.md",
    "templates": "TEMPLATE_GUIDE.md",
    "plugins": "PLUGIN_GUIDE.md",
    "troubleshooting": "TROUBLESHOOTING.md",
    "ffmpeg": "FFMPEG_SETUP.md",
    "foundation": "FOUNDATION_SYSTEMS.md",
    "charter": "PRODUCT_ENGINEERING_CHARTER.md",
    "local-ai": "LOCAL_AI_SETUP.md",
    "developer": "DEVELOPER_GUIDE.md",
    "plugin-api": "PLUGIN_API.md",
    "schema": "JSON_SCHEMA_REFERENCE.md",
    "mvp": "MVP_ROADMAP.md",
    "content-generator": "CONTENT_GENERATOR_MODE.md",
    "content-review": "CONTENT_REVIEW_WORKFLOW.md",
    "posting-package": "POSTING_PACKAGE.md",
    "workflow-automation": "CREATOR_WORKFLOW_AUTOMATION.md",
    "quality-feedback": "QUALITY_FEEDBACK_LOOPS.md",
    "long-term-evolution": "LONG_TERM_EVOLUTION.md",
    "beginner-auto-template": "BEGINNER_AUTO_TEMPLATE_MODE.md",
    "media-compatibility": "MEDIA_COMPATIBILITY.md",
    "interactive-preview": "INTERACTIVE_PREVIEW_MODE.md",
    "preview-review": "PREVIEW_REVIEW_EDIT_CONTROL.md",
    "final-preflight": "FINAL_REVIEW_PREFLIGHT.md",
    "shorts": "YOUTUBE_SHORTS_MODE.md",
    "beginner": "BEGINNER_TUTORIAL.md",
    "advanced": "ADVANCED_WORKFLOWS.md",
    "advanced-systems": "ADVANCED_SYSTEMS.md",
    "adaptive-workflow": "ADAPTIVE_WORKFLOW_INTELLIGENCE.md",
    "proactive-assistance": "PROACTIVE_CREATIVE_ASSISTANCE.md",
    "autonomous-pipeline": "AUTONOMOUS_PRODUCTION_PIPELINE.md",
    "release": "RELEASE_CHECKLIST.md",
    "changelog": "CHANGELOG.md",
    "showcase": "SHOWCASE_MODE.md",
}


def docs_root() -> Path:
    return Path(__file__).resolve().parents[2] / "docs"


def list_docs() -> list[dict[str, str]]:
    root = docs_root()
    return [{"key": key, "path": str((root / filename).resolve()), "title": _title(root / filename)} for key, filename in DOCS.items()]


def read_doc(key: str) -> str:
    if key not in DOCS:
        raise KeyError(f"Unknown doc '{key}'. Expected one of: {', '.join(sorted(DOCS))}")
    return (docs_root() / DOCS[key]).read_text(encoding="utf-8")


def _title(path: Path) -> str:
    if not path.exists():
        return path.stem.replace("_", " ").title()
    first = path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
    return first or path.stem.replace("_", " ").title()
