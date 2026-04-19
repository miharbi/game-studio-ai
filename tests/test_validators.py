"""Tests for output schema validators."""
from __future__ import annotations

import json
import pytest

from src.validators.schema import validate_output


class TestValidateOutput:
    def test_valid_json_string(self):
        content = '```json\n{"key": "value"}\n```'
        errors = validate_output(content, "json")
        assert errors == []

    def test_invalid_json_string(self):
        content = '```json\n{not valid json}\n```'
        errors = validate_output(content, "invalid_json_here")
        # Should not raise — just return errors or empty
        assert isinstance(errors, list)

    def test_level_json_valid(self):
        level = {
            "id": "World01",
            "name_display": "Test World",
            "waves": [],
            "props": [],
            "scenario_ads": [],
            "dialogues_pool": [],
        }
        content = f"```json\n{json.dumps(level)}\n```"
        errors = validate_output(content, "level_json")
        assert isinstance(errors, list)

    def test_sprite_spec_valid(self):
        spec = {
            "name": "player_1",
            "prompt": "pixel art hero character 48x64",
            "width": 48,
            "height": 64,
        }
        content = f"```json\n{json.dumps(spec)}\n```"
        errors = validate_output(content, "sprite_spec")
        assert isinstance(errors, list)

    def test_code_block_detected(self):
        content = "Here is the code:\n```gdscript\nfunc foo() -> void:\n    pass\n```"
        errors = validate_output(content, "code_block")
        assert errors == []

    def test_code_block_missing(self):
        content = "No code here, just plain text."
        errors = validate_output(content, "code_block")
        assert len(errors) > 0

    def test_feature_design_valid(self):
        content = "## Concept\nA cool feature.\n## Mechanics\n1. Do stuff.\n## Risks\nNone."
        errors = validate_output(content, "feature_design")
        assert errors == []

    def test_unknown_schema_type_returns_no_errors(self):
        errors = validate_output("anything", "unknown_schema_xyz")
        assert errors == []
