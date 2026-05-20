from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ProjectValidationError(ValueError):
    pass


def _format_path(path_parts: list[Any]) -> str:
    if not path_parts:
        return "$"
    path = "$"
    for part in path_parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def validate_project(data: dict[str, Any]) -> None:
    errors = get_validation_errors(data)
    if not errors:
        return

    lines = ["Project JSON failed validation:"]
    for error in errors:
        lines.append(f"- {_format_path(list(error.absolute_path))}: {error.message}")
    raise ProjectValidationError("\n".join(lines))


def get_validation_errors(data: dict[str, Any]):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'jsonschema'. Run: python -m pip install -r requirements.txt"
        ) from exc

    schema_path = Path(__file__).with_name("project.schema.json")
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)

    validator = Draft202012Validator(schema)
    return sorted(validator.iter_errors(data), key=lambda error: list(error.absolute_path))
