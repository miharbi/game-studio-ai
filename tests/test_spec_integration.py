"""
Tests: sdd-custom spec file integration with game-studio-ai.

Covers:
  - Spec file loading into engine context (loader)
  - Per-agent context injection (orchestrator/context)
  - Barrio Bravo world validator (validators/godot4_world)
  - World merger (mergers/godot4_world)
  - Difficulty skeleton generator (generators/godot4_skeleton)
"""
from __future__ import annotations

import json
import copy
from pathlib import Path
from typing import Any

import pytest

from src.engines.loader import load_engine_context
from src.orchestrator.context import build_agent_context
from src.validators.godot4_world import validate_world, ValidationResult
from src.mergers.godot4_world import merge_world, _assign_ad_positions
from src.generators.godot4_skeleton import (
    compute_skeleton,
    extract_prev_stats,
    PrevWorldStats,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    """Create a minimal fake sdd-custom project layout."""
    project_root = tmp_path / "sdd-custom"
    project_root.mkdir()
    (project_root / "project.godot").write_text("[gd_resource]")

    game_spec: dict[str, Any] = {
        "meta": {"project": "Test Game", "engine": "godot4"},
        "art_style": {"technique": "pixel art"},
        "characters": [{"key": "player_1", "sprite_size_px": "48x64"}],
        "audio": {
            "music": [{"key": "main_menu", "style_brief": "upbeat"}],
            "sfx": [{"key": "punch", "implemented": True}],
        },
        "vfx": [{"key": "hit_spark", "frames": 4}],
        "sample_assets": {},
        "world_authoring": {"template_path": "data/level_template.json"},
    }
    (project_root / "data").mkdir()
    (project_root / "data" / "game_spec.json").write_text(
        json.dumps(game_spec), encoding="utf-8"
    )

    level_template: dict[str, Any] = {"id": "WorldNN", "waves": []}
    (project_root / "data" / "level_template.json").write_text(
        json.dumps(level_template), encoding="utf-8"
    )

    return project_root


@pytest.fixture
def minimal_world() -> dict[str, Any]:
    """A schema-valid minimal Barrio Bravo world dict."""
    art = {k: "A descriptive sentence." for k in [
        "bg_far_1", "bg_far_2", "bg_far_3", "bg_far_4", "bg_far_5", "bg_far_6",
        "building_01", "building_02", "building_03", "building_04", "building_05",
        "building_06", "building_07", "building_08", "building_09", "building_10",
        "building_11", "sidewalk", "ground",
    ]}
    art["wall_color"] = "#C47A3A"

    return {
        "id": "World03",
        "name_display": "El Cementerio Electrico",
        "background_key": "World03Bg",
        "music_key": "world_03_theme",
        "scroll_limit_px": 3500,
        "camera_y": 475.0,
        "player_spawn": {
            "p1": {"x": 80.0, "y_lane": 0.5},
            "p2": {"x": 50.0, "y_lane": 0.6},
        },
        "lanes": {
            "y_top": 530,
            "y_bottom": 575,
            "depth_scale_min": 0.7,
            "depth_scale_max": 1.0,
        },
        "waves": [
            {
                "id": "wave_01",
                "trigger_x": 500.0,
                "lock_camera": True,
                "intro": [
                    {"speaker": "enemy", "text": "Aqui no pasa nada, chico."},
                    {"speaker": "player_1", "text": "Ya veremos."},
                ],
                "enemies": [{"type": "enemy_1", "count": 1, "x": 570.0, "lane": 0.5}],
            },
            {
                "id": "wave_02",
                "trigger_x": 1000.0,
                "lock_camera": True,
                "intro": [
                    {"speaker": "enemy", "text": "Refuerzos llegaron!"},
                    {"speaker": "player_1", "text": "Siguen cayendo."},
                ],
                "enemies": [{"type": "enemy_2", "count": 1, "x": 1070.0, "lane": 0.4}],
            },
            {
                "id": "wave_boss",
                "trigger_x": 2800.0,
                "lock_camera": True,
                "intro": [
                    {"speaker": "boss", "text": "Aqui termina tu camino!"},
                    {"speaker": "player_1", "text": "No lo creo."},
                ],
                "enemies": [{"type": "boss_2", "count": 1, "x": 2870.0, "lane": 0.5}],
            },
        ],
        "boss": {
            "type": "boss_2",
            "name": "El Bachaquero",
            "intro_dialogue": "boss_intro_w3",
            "defeat_dialogue": "boss_defeat_w3",
        },
        "props": [
            {"type": "lamppost",    "x": 200.0, "y_lane": 0.3},
            {"type": "dumpster",    "x": 600.0, "y_lane": 0.4, "throwable": True},
            {"type": "street_food", "x": 900.0, "y_lane": 0.5, "destructible": True},
            {"type": "lamppost",    "x": 1300.0, "y_lane": 0.6},
        ],
        "scenario_ads": [
            {"type": "billboard", "text": "CLAP Box 2.0", "subtext": "Menos comida, mas aire"},
            {"type": "graffiti",  "text": "Resistencia!"},
            {"type": "billboard", "text": "Dolares solo en efectivo"},
            {"type": "graffiti",  "text": "El pueblo no se rinde"},
        ],
        "dialogues_pool": [
            {"id": "enc_w3_01",  "speaker": "enemy",    "text": "Spawn line 1",    "trigger": "spawn"},
            {"id": "enc_w3_02",  "speaker": "enemy",    "text": "Spawn line 2",    "trigger": "spawn"},
            {"id": "enc_w3_03",  "speaker": "enemy",    "text": "Spawn line 3",    "trigger": "spawn"},
            {"id": "combo_w3_01","speaker": "player_1", "text": "Combo line 1",    "trigger": "combo_3"},
            {"id": "combo_w3_02","speaker": "player_1", "text": "Combo line 2",    "trigger": "combo_3"},
            {"id": "hit_w3_01",  "speaker": "player_1", "text": "Hit line 1",      "trigger": "hit"},
            {"id": "hit_w3_02",  "speaker": "player_1", "text": "Hit line 2",      "trigger": "hit"},
            {"id": "bi_w3",      "speaker": "boss",     "text": "Boss intro",      "trigger": "boss_spawn"},
            {"id": "bp2_w3",     "speaker": "boss",     "text": "Boss phase 2",    "trigger": "boss_phase2"},
            {"id": "bd_w3",      "speaker": "boss",     "text": "Boss defeated",   "trigger": "boss_defeat"},
            {"id": "lh_w3_01",   "speaker": "player_1", "text": "Low health line", "trigger": "low_health"},
        ],
        "art_direction": art,
        "next_world": "World04",
    }


@pytest.fixture
def fake_levels(tmp_path: Path, minimal_world: dict[str, Any]) -> Path:
    """A minimal levels_fallback.json with World01 and World02."""
    art = {k: "desc" for k in [
        "bg_far_1", "bg_far_2", "bg_far_3", "bg_far_4", "bg_far_5", "bg_far_6",
        "building_01", "building_02", "building_03", "building_04", "building_05",
        "building_06", "building_07", "building_08", "building_09", "building_10",
        "building_11", "sidewalk", "ground",
    ]}
    art["wall_color"] = "#C47A3A"

    def _base_world(wid: str, scroll: int) -> dict[str, Any]:
        return {
            "id": wid,
            "name_display": wid,
            "background_key": f"{wid}Bg",
            "music_key": "test_music",
            "scroll_limit_px": scroll,
            "camera_y": 475.0,
            "player_spawn": {
                "p1": {"x": 80.0, "y_lane": 0.5},
                "p2": {"x": 50.0, "y_lane": 0.6},
            },
            "lanes": {"y_top": 530, "y_bottom": 575,
                      "depth_scale_min": 0.7, "depth_scale_max": 1.0},
            "waves": [
                {
                    "id": "wave_01", "trigger_x": 500.0, "lock_camera": True,
                    "intro": [{"speaker": "enemy", "text": "Hey"}, {"speaker": "player_1", "text": "Ok"}],
                    "enemies": [{"type": "enemy_1", "count": 1, "x": 570.0, "lane": 0.5}],
                },
                {
                    "id": "wave_boss", "trigger_x": 1000.0, "lock_camera": True,
                    "intro": [{"speaker": "boss", "text": "Boss"}, {"speaker": "player_1", "text": "Ok"}],
                    "enemies": [{"type": "boss_1", "count": 1, "x": 1070.0, "lane": 0.5}],
                },
            ],
            "boss": {"type": "boss_1", "name": "El Jefe", "intro_dialogue": "bi", "defeat_dialogue": "bd"},
            "props": [
                {"type": "street_food", "x": 700.0, "y_lane": 0.5, "destructible": True},
            ],
            "scenario_ads": [
                {"type": "billboard", "x": 300.0, "text": "Ad 1"},
                {"type": "graffiti",  "x": 700.0, "text": "Ad 2"},
                {"type": "billboard", "x": 1100.0, "text": "Ad 3"},
                {"type": "graffiti",  "x": 1500.0, "text": "Ad 4"},
            ],
            "dialogues_pool": [
                {"id": f"d{i}", "speaker": "enemy", "text": f"line {i}", "trigger": "spawn"}
                for i in range(11)
            ],
            "art_direction": art,
        }

    data: dict[str, Any] = {
        "schema_version": "1.0.0",
        "worlds": [_base_world("World01", 3096), _base_world("World02", 3496)],
    }
    path = tmp_path / "levels_fallback.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Spec file loader tests
# ---------------------------------------------------------------------------

class TestSpecLoader:
    def test_spec_files_loaded_into_engine_context(self, fake_project: Path) -> None:
        ctx = load_engine_context(fake_project)
        assert "spec_files" in ctx, "engine context must have a spec_files key"
        assert "data/game_spec.json" in ctx["spec_files"]
        assert "data/level_template.json" in ctx["spec_files"]
        assert ctx["spec_files"]["data/game_spec.json"]["meta"]["engine"] == "godot4"

    def test_missing_spec_file_does_not_raise(self, fake_project: Path) -> None:
        (fake_project / "data" / "game_spec.json").unlink()
        ctx = load_engine_context(fake_project)
        spec_files = ctx.get("spec_files", {})
        assert "data/game_spec.json" not in spec_files

    def test_non_godot_project_returns_empty_spec_files(self, tmp_path: Path) -> None:
        (tmp_path / "project.sln").write_text("")
        ctx = load_engine_context(tmp_path)
        assert ctx["spec_files"] == {} or "data/game_spec.json" not in ctx.get("spec_files", {})

    def test_engine_id_is_godot4(self, fake_project: Path) -> None:
        ctx = load_engine_context(fake_project)
        assert ctx["engine_id"] == "godot4"

    def test_engine_context_string_present(self, fake_project: Path) -> None:
        ctx = load_engine_context(fake_project)
        assert len(ctx["agent_context"]) > 10


# ---------------------------------------------------------------------------
# Per-agent context injection tests
# ---------------------------------------------------------------------------

class TestAgentContext:
    def test_art_director_context_includes_art_style(self, fake_project: Path) -> None:
        engine_ctx = load_engine_context(fake_project)
        result = build_agent_context("art_director", engine_ctx)
        assert "art_style" in result or "pixel art" in result

    def test_audio_director_context_includes_sfx(self, fake_project: Path) -> None:
        engine_ctx = load_engine_context(fake_project)
        result = build_agent_context("audio_director", engine_ctx)
        assert "punch" in result

    def test_level_designer_context_includes_template(self, fake_project: Path) -> None:
        engine_ctx = load_engine_context(fake_project)
        result = build_agent_context("level_designer", engine_ctx)
        assert "WorldNN" in result

    def test_world_builder_context_includes_template(self, fake_project: Path) -> None:
        engine_ctx = load_engine_context(fake_project)
        result = build_agent_context("world_builder", engine_ctx)
        assert "WorldNN" in result

    def test_unknown_agent_gets_meta_only(self, fake_project: Path) -> None:
        engine_ctx = load_engine_context(fake_project)
        result = build_agent_context("unknown_agent", engine_ctx)
        assert "Test Game" in result  # from meta.project

    def test_empty_spec_files_returns_empty_string(self) -> None:
        result = build_agent_context("art_director", {"spec_files": {}})
        assert result == ""


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------

class TestWorldValidator:
    def test_valid_world_passes(self, minimal_world: dict[str, Any]) -> None:
        result = validate_world(minimal_world, prev_boss_hp=500)
        assert result.passed, result.report()

    def test_validator_rejects_missing_keys(self, minimal_world: dict[str, Any]) -> None:
        del minimal_world["name_display"]
        result = validate_world(minimal_world)
        assert not result.passed
        assert any("name_display" in e for e in result.errors)

    def test_validator_rejects_empty_name_display(self, minimal_world: dict[str, Any]) -> None:
        minimal_world["name_display"] = "   "
        result = validate_world(minimal_world)
        assert not result.passed

    def test_validator_rejects_bad_lane(self, minimal_world: dict[str, Any]) -> None:
        minimal_world["waves"][0]["enemies"][0]["lane"] = 1.5
        result = validate_world(minimal_world)
        assert not result.passed
        assert any("lane=1.5" in e for e in result.errors)

    def test_validator_rejects_insufficient_street_food(
        self, minimal_world: dict[str, Any]
    ) -> None:
        # 2 combat waves → need 1 street_food; remove all food props
        minimal_world["props"] = [
            p for p in minimal_world["props"] if p["type"] != "street_food"
        ]
        result = validate_world(minimal_world)
        assert not result.passed
        assert any("street_food" in e for e in result.errors)

    def test_validator_rejects_too_few_ads(self, minimal_world: dict[str, Any]) -> None:
        minimal_world["scenario_ads"] = minimal_world["scenario_ads"][:2]
        result = validate_world(minimal_world)
        assert not result.passed
        assert any("scenario_ads" in e for e in result.errors)

    def test_validator_rejects_duplicate_dialogue_ids(
        self, minimal_world: dict[str, Any]
    ) -> None:
        minimal_world["dialogues_pool"].append(
            {"id": "enc_w3_01", "speaker": "enemy", "text": "dup", "trigger": "spawn"}
        )
        result = validate_world(minimal_world)
        assert not result.passed
        assert any("enc_w3_01" in e for e in result.errors)

    def test_validator_rejects_invalid_trigger(
        self, minimal_world: dict[str, Any]
    ) -> None:
        minimal_world["dialogues_pool"][0]["trigger"] = "not_a_trigger"
        result = validate_world(minimal_world)
        assert not result.passed

    def test_validator_rejects_invented_top_level_key(
        self, minimal_world: dict[str, Any]
    ) -> None:
        minimal_world["invented_key"] = "oops"
        result = validate_world(minimal_world)
        assert not result.passed

    def test_validator_rejects_missing_art_direction_key(
        self, minimal_world: dict[str, Any]
    ) -> None:
        del minimal_world["art_direction"]["sidewalk"]
        result = validate_world(minimal_world)
        assert not result.passed

    def test_validator_warns_about_boss_hp_scaling(
        self, minimal_world: dict[str, Any]
    ) -> None:
        result = validate_world(minimal_world, prev_boss_hp=500)
        assert any("health" in w or "HP" in w for w in result.warnings)

    def test_validator_rejects_wave_trigger_gap_too_small(
        self, minimal_world: dict[str, Any]
    ) -> None:
        # Set wave_02 trigger only 100px after wave_01
        minimal_world["waves"][1]["trigger_x"] = 600.0
        result = validate_world(minimal_world)
        assert not result.passed
        assert any("gap" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Merger tests
# ---------------------------------------------------------------------------

class TestWorldMerger:
    def test_merger_assigns_ad_x(
        self, fake_levels: Path, minimal_world: dict[str, Any]
    ) -> None:
        # Remove existing x values from ads
        for ad in minimal_world["scenario_ads"]:
            ad.pop("x", None)
        merge_world(fake_levels, copy.deepcopy(minimal_world))
        data = json.loads(fake_levels.read_text())
        merged = next(w for w in data["worlds"] if w["id"] == "World03")
        for ad in merged["scenario_ads"]:
            assert "x" in ad, "merger must assign x to all scenario_ads"
            assert isinstance(ad["x"], float)

    def test_merger_chains_next_world(
        self, fake_levels: Path, minimal_world: dict[str, Any]
    ) -> None:
        merge_world(fake_levels, copy.deepcopy(minimal_world))
        data = json.loads(fake_levels.read_text())
        world02 = next(w for w in data["worlds"] if w["id"] == "World02")
        assert world02.get("next_world") == "World03"

    def test_merger_appends_world(
        self, fake_levels: Path, minimal_world: dict[str, Any]
    ) -> None:
        before = json.loads(fake_levels.read_text())
        count_before = len(before["worlds"])
        merge_world(fake_levels, copy.deepcopy(minimal_world))
        after = json.loads(fake_levels.read_text())
        assert len(after["worlds"]) == count_before + 1

    def test_merger_creates_backup(
        self, fake_levels: Path, minimal_world: dict[str, Any]
    ) -> None:
        merge_world(fake_levels, copy.deepcopy(minimal_world))
        backup = fake_levels.with_name("levels_fallback.backup.json")
        assert backup.exists()

    def test_merger_atomic_write(
        self, fake_levels: Path, minimal_world: dict[str, Any], monkeypatch
    ) -> None:
        """Simulate a crash mid-write: original file must remain intact."""
        original_content = fake_levels.read_text()

        import src.mergers.godot4_world as merger_mod

        def crash(*_args, **_kwargs):
            raise OSError("simulated crash")

        monkeypatch.setattr(merger_mod.os, "replace", crash)

        with pytest.raises(OSError):
            merge_world(fake_levels, copy.deepcopy(minimal_world))

        assert fake_levels.read_text() == original_content

    def test_merger_raises_for_missing_file(
        self, tmp_path: Path, minimal_world: dict[str, Any]
    ) -> None:
        missing = tmp_path / "levels_fallback.json"
        with pytest.raises(FileNotFoundError):
            merge_world(missing, minimal_world)

    def test_assign_ad_positions_evenly_distributed(self) -> None:
        world: dict = {
            "scroll_limit_px": 3000,
            "scenario_ads": [{"type": "billboard", "text": "A"} for _ in range(4)],
        }
        _assign_ad_positions(world)
        xs = [ad["x"] for ad in world["scenario_ads"]]
        assert all(x > 0 for x in xs)
        assert xs == sorted(xs), "x positions must be ascending"


# ---------------------------------------------------------------------------
# Skeleton generator tests
# ---------------------------------------------------------------------------

class TestSkeletonGenerator:
    @pytest.fixture
    def prev_stats(self) -> PrevWorldStats:
        return PrevWorldStats(
            world_num=2,
            scroll_limit_px=3496,
            boss_hp=500,
            wave_count=4,
            combat_wave_count=3,
            camera_y=475.0,
            lanes={"y_top": 530, "y_bottom": 575,
                   "depth_scale_min": 0.7, "depth_scale_max": 1.0},
        )

    def test_skeleton_boss_hp_scaling(self, prev_stats: PrevWorldStats) -> None:
        skel = compute_skeleton(prev_stats, seed=42)
        meta_hp = skel["_meta_boss_hp"]
        assert meta_hp == int(500 * 1.25), f"Expected 625, got {meta_hp}"

    def test_skeleton_wave_gap(self, prev_stats: PrevWorldStats) -> None:
        skel = compute_skeleton(prev_stats, seed=42)
        waves = skel["waves"]
        triggers = [w["trigger_x"] for w in waves]
        for i in range(1, len(triggers)):
            gap = triggers[i] - triggers[i - 1]
            assert gap >= 400, f"Wave gap {gap}px is less than 400px"

    def test_skeleton_id_incremented(self, prev_stats: PrevWorldStats) -> None:
        skel = compute_skeleton(prev_stats, seed=1)
        assert skel["id"] == "World03"

    def test_skeleton_has_boss_wave(self, prev_stats: PrevWorldStats) -> None:
        skel = compute_skeleton(prev_stats, seed=1)
        wave_ids = [w["id"] for w in skel["waves"]]
        assert "wave_boss" in wave_ids

    def test_skeleton_scroll_limit_increased(self, prev_stats: PrevWorldStats) -> None:
        skel = compute_skeleton(prev_stats, seed=1)
        assert skel["scroll_limit_px"] == 3496 + 400

    def test_skeleton_meta_boss_hp_stripped_before_validate(
        self, prev_stats: PrevWorldStats, minimal_world: dict[str, Any]
    ) -> None:
        """_meta_boss_hp must be absent before validation passes."""
        skel = compute_skeleton(prev_stats, seed=1)
        assert "_meta_boss_hp" in skel
        skel.pop("_meta_boss_hp")
        assert "_meta_boss_hp" not in skel

    def test_extract_prev_stats_from_levels_data(self, fake_levels: Path) -> None:
        data = json.loads(fake_levels.read_text())
        prev = extract_prev_stats(data)
        assert prev.world_num == 2
        assert prev.scroll_limit_px == 3496
        assert prev.boss_hp == 500  # default when no enemies table

    def test_extract_prev_stats_raises_on_empty(self) -> None:
        with pytest.raises(ValueError):
            extract_prev_stats({"worlds": []})

    def test_skeleton_props_include_street_food(self, prev_stats: PrevWorldStats) -> None:
        skel = compute_skeleton(prev_stats, seed=5)
        food = [p for p in skel["props"] if p["type"] == "street_food"]
        assert len(food) >= 1
