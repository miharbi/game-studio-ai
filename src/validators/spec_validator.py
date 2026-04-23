"""Generic spec-file-driven validator.

Reads ``config/validators.yaml`` to find user-defined validators.
Each entry maps a name to a ``source_spec`` file path plus optional settings.

Usage::

    from src.validators.spec_validator import validate_with_spec, derive_rules, load_validators

    errors = validate_with_spec(agent_output, "my_validator")
    rules  = derive_rules("/path/to/spec.json")
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_VALIDATORS_PATH = Path(__file__).resolve().parents[2] / "config" / "validators.yaml"


def load_validators() -> dict[str, dict]:
    """Load ``config/validators.yaml`` — returns ``{}`` if missing or invalid."""
    try:
        data = yaml.safe_load(_VALIDATORS_PATH.read_text()) or {}
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def derive_rules(spec_file_path: str) -> dict[str, Any]:
    """Derive validation rules from a spec JSON file.

    Inspects the file for a top-level ``_schema`` block and extracts:

    * ``required_keys`` — every top-level key except ``_schema``
    * ``enums`` — ``{field: [allowed_value, ...]}`` built from ``_schema.valid_*`` lists

    Returns ``{}`` if the file cannot be read or parsed.
    """
    try:
        p = Path(spec_file_path)
        if not p.is_file():
            return {}
        data = json.loads(p.read_text())
        if not isinstance(data, dict):
            return {}
        schema_block = data.get("_schema") if isinstance(data.get("_schema"), dict) else {}
        required_keys = [k for k in data if k != "_schema"]
        enums: dict[str, list[str]] = {}
        for key, value in (schema_block or {}).items():
            if key.startswith("valid_") and isinstance(value, list):
                field = key[len("valid_"):]
                enums[field] = [str(v) for v in value]
        return {"required_keys": required_keys, "enums": enums}
    except Exception:
        return {}


def validate_with_spec(content: str, validator_name: str) -> list[str]:
    """Validate agent output JSON using a named user-defined validator.

    Looks up *validator_name* in ``config/validators.yaml``, derives rules
    from its ``source_spec`` file, and checks the parsed JSON against those
    rules.  Returns an empty list when:

    * the validator name is not registered (treated as no-op),
    * the spec file cannot be read (rules cannot be derived).

    Returns a list of error strings on failure.
    """
    validators = load_validators()
    entry = validators.get(validator_name)
    if not isinstance(entry, dict):
        return []

    spec_file = entry.get("source_spec", "")
    if not spec_file:
        return []

    rules = derive_rules(spec_file)
    if not rules:
        return []

    text = _extract_json_block(content)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    if not isinstance(data, dict):
        return ["Expected a JSON object"]

    errors: list[str] = []

    # Required top-level keys
    missing = [k for k in rules.get("required_keys", []) if k not in data]
    if missing:
        errors.append(f"Missing required keys: {missing}")

    # Enum constraints
    for field, allowed in rules.get("enums", {}).items():
        if field not in data:
            continue
        value = data[field]
        if isinstance(value, str) and value not in allowed:
            errors.append(f"Invalid {field!r}: {value!r} not in allowed values")
        elif isinstance(value, list):
            bad = [v for v in value if v not in allowed]
            if bad:
                errors.append(f"Invalid {field!r} values: {bad}")

    return errors


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
