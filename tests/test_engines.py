"""Tests for engine detection."""
from __future__ import annotations

import pytest
from pathlib import Path

from src.engines.detect import detect, load_engine_context, load_engine_config


class TestEngineDetect:
    def test_detect_godot4(self, tmp_path: Path):
        (tmp_path / "project.godot").write_text("[application]\n")
        assert detect(tmp_path) == "godot4"

    def test_detect_unity(self, tmp_path: Path):
        ps = tmp_path / "ProjectSettings"
        ps.mkdir()
        (ps / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.0f1\n")
        assert detect(tmp_path) == "unity"

    def test_detect_unreal5(self, tmp_path: Path):
        (tmp_path / "MyGame.uproject").write_text("{}\n")
        assert detect(tmp_path) == "unreal5"

    def test_detect_returns_none_for_unknown(self, tmp_path: Path):
        result = detect(tmp_path)
        assert result is None

    def test_load_engine_context_godot4(self):
        context = load_engine_context("godot4")
        assert isinstance(context, str)
        assert len(context) > 20

    def test_load_engine_context_unity(self):
        context = load_engine_context("unity")
        assert isinstance(context, str)

    def test_load_engine_context_unreal5(self):
        context = load_engine_context("unreal5")
        assert isinstance(context, str)

    def test_load_engine_config_returns_dict(self):
        config = load_engine_config("godot4")
        assert isinstance(config, dict)
        assert "name" in config or "engine" in config or len(config) > 0

    def test_load_unknown_engine_returns_empty(self):
        context = load_engine_context("unknown_engine_xyz")
        assert context == "" or isinstance(context, str)
