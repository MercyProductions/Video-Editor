from __future__ import annotations

import ast
import json
import time
from pathlib import Path
from typing import Any

from docs.local_docs import list_docs
from engines.registry import engine_registry
from plugins.registry import audit_plugins


def architecture_audit(*, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    python_files = sorted(src.rglob("*.py"))
    package_counts = _package_counts(python_files, src)
    long_functions = _long_functions(python_files)
    deprecated_terms = _deprecated_terms(root)
    docs = list_docs()
    plugin_audit = audit_plugins()
    registry = engine_registry()
    warnings = []
    if long_functions:
        warnings.append(f"{len(long_functions)} large functions need future refactoring attention.")
    if deprecated_terms:
        warnings.append("Some local-first UI/API names still use legacy marketplace wording.")
    if plugin_audit["warnings"]:
        warnings.append(f"{len(plugin_audit['warnings'])} plugin audit warnings remain.")
    if len(docs) < 10:
        warnings.append("Documentation set is smaller than the release candidate target.")

    report = {
        "format": "automatic-video-editor-architecture-audit",
        "createdAt": _now(),
        "root": str(root.resolve()),
        "summary": {
            "pythonFileCount": len(python_files),
            "packageCount": len(package_counts),
            "docCount": len(docs),
            "pluginCount": plugin_audit["pluginCount"],
            "warningCount": len(warnings),
        },
        "engines": registry,
        "packageCounts": package_counts,
        "largeFunctions": long_functions[:40],
        "legacyNaming": deprecated_terms[:40],
        "docs": docs,
        "pluginAudit": plugin_audit,
        "recommendations": _recommendations(long_functions, deprecated_terms, plugin_audit),
        "warnings": warnings,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _package_counts(files: list[Path], src: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in files:
        rel = path.relative_to(src)
        package = rel.parts[0] if len(rel.parts) > 1 else "_root"
        counts[package] = counts.get(package, 0) + 1
    return dict(sorted(counts.items()))


def _long_functions(files: list[Path], *, threshold: int = 90) -> list[dict[str, Any]]:
    rows = []
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(node, "end_lineno", None):
                lines = int(node.end_lineno or node.lineno) - int(node.lineno) + 1
                if lines >= threshold:
                    rows.append({"file": str(path.resolve()), "function": node.name, "start": node.lineno, "lines": lines})
    return sorted(rows, key=lambda item: item["lines"], reverse=True)


def _deprecated_terms(root: Path) -> list[dict[str, Any]]:
    terms = ("marketplace",)
    rows = []
    for path in [*list((root / "src").rglob("*.py")), *list((root / "desktop-app" / "src").rglob("*.tsx"))]:
        if any(part in {"node_modules", "dist"} for part in path.parts):
            continue
        if path.name == "audit.py" or path.name == "local_policy.py":
            continue
        try:
            for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                lowered = line.lower()
                if any(term in lowered for term in terms):
                    rows.append({"file": str(path.resolve()), "line": index, "text": line.strip()[:140]})
        except UnicodeDecodeError:
            continue
    return rows


def _recommendations(long_functions: list[dict[str, Any]], deprecated_terms: list[dict[str, Any]], plugin_audit: dict[str, Any]) -> list[str]:
    recommendations = []
    if long_functions:
        recommendations.append("Split the largest CLI handlers and render methods only when a concrete bug or test pressure appears.")
    if deprecated_terms:
        recommendations.append("Rename user-facing marketplace labels to offline packs during the next UI copy pass.")
    if plugin_audit["warnings"]:
        recommendations.append("Resolve plugin audit warnings before publishing plugin examples.")
    recommendations.append("Keep JSON schema and renderer behavior in lockstep by validating every generated demo during release checks.")
    return recommendations


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
