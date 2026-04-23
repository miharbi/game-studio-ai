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

    def test_invalid_json_raises_error(self):
        content = '```json\n{not valid json}\n```'
        errors = validate_output(content, "json")
        assert len(errors) > 0

    def test_json_without_fence(self):
        errors = validate_output('{"key": "value"}', "json")
        assert errors == []

    def test_unknown_schema_type_returns_no_errors(self):
        errors = validate_output("anything", "unknown_schema_xyz")
        assert errors == []
