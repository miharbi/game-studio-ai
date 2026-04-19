"""Output validation for common agent output types.

Returns a list of error strings (empty list = valid).
"""
from __future__ import annotations

import json
from typing import Any


def validate_output(content: str, schema_type: str) -> list[str]:
    """
    Validate agent output against a named schema type.
    Returns list of error strings; empty list = valid.
    """
    validators = {
        "json": _validate_json,
        "level_json": _validate_level_json,
        "sprite_spec": _validate_sprite_spec,
        "code_block": _validate_code_block,
        "feature_design": _validate_feature_design,
    }
    fn = validators.get(schema_type)
    if fn is None:
        return []
    return fn(content)


def _validate_json(content: str) -> list[str]:
    text = _extract_json_block(content)
    try:
        json.loads(text)
        return []
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]


def _validate_level_json(content: str) -> list[str]:
    errors = _validate_json(content)
    if errors:
        return errors
    data: dict[str, Any] = json.loads(_extract_json_block(content))
    required_keys = ["id", "name_display", "waves", "props", "scenario_ads"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        errors.append(f"Missing required level keys: {missing}")
    if "lanes" in data:
        lanes = data["lanes"]
        if not (0.0 <= lanes.get("y_top", 0) < lanes.get("y_bottom", 1)):
            errors.append("lanes.y_top must be less than lanes.y_bottom")
    return errors


def _validate_sprite_spec(content: str) -> list[str]:
    errors = _validate_json(content)
    if errors:
        return errors
    data: dict[str, Any] = json.loads(_extract_json_block(content))
    # Accept both formats: {name, type, prompt, dimensions} or {name, prompt, width, height}
    missing = [k for k in ("name", "prompt") if k not in data]
    has_dimensions = "dimensions" in data
    has_wh = "width" in data and "height" in data
    if not has_dimensions and not has_wh:
        missing.append("dimensions (or width+height)")
    if missing:
        errors.append(f"Missing sprite spec keys: {missing}")
    return errors


def _validate_code_block(content: str) -> list[str]:
    if "```" not in content:
        return ["Expected a fenced code block (```) in output"]
    return []


def _validate_feature_design(content: str) -> list[str]:
    required_sections = ["## Concept", "## Mechanics", "## Risks"]
    missing = [s for s in required_sections if s not in content]
    if missing:
        return [f"Feature design missing sections: {missing}"]
    return []


def _extract_json_block(content: str) -> str:
    """Extract JSON from a markdown code fence if present."""
    if "```json" in content:
        start = content.index("```json") + 7
        end = content.index("```", start)
        return content[start:end].strip()
    if "```" in content:
        start = content.index("```") + 3
        end = content.index("```", start)
        return content[start:end].strip()
    return content.strip()
