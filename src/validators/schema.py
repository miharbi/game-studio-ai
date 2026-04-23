"""Output validation for common agent output types.

Returns a list of error strings (empty list = valid).
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

_SCHEMA_TYPES_PATH = Path(__file__).resolve().parents[2] / "config" / "schema_types.yaml"

_BUILTIN_SCHEMA_TYPES: list[str] = ["json"]


def _load_schema_types() -> list[str]:
    """Load schema types from config/schema_types.yaml, falling back to builtins."""
    try:
        data = yaml.safe_load(_SCHEMA_TYPES_PATH.read_text()) or {}
        types = data.get("schema_types", [])
        if isinstance(types, list) and types:
            return [str(t) for t in types]
    except Exception:
        pass
    return list(_BUILTIN_SCHEMA_TYPES)


def validate_output(content: str, schema_type: str) -> list[str]:
    """
    Validate agent output against a named schema type.

    Built-in types: ``json``.
    User-defined types are looked up in config/validators.yaml — unknown
    types are silently skipped (returns []).
    """
    if schema_type == "json":
        return _validate_json(content)
    # Delegate to the spec-file-driven validator for user-defined types
    from src.validators.spec_validator import validate_with_spec
    return validate_with_spec(content, schema_type)


# Exported list of valid schema type names — loaded from config/schema_types.yaml at import
# time. Unknown custom types pass through validate_output() as no-ops.
SCHEMA_TYPES: list[str] = _load_schema_types()


def _validate_json(content: str) -> list[str]:
    text = _extract_json_block(content)
    try:
        json.loads(text)
        return []
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]


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
