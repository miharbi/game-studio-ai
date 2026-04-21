"""Validate a Barrio Bravo world JSON block before merging into levels_fallback.json.

All rules are deterministic and require no API call.

Usage::

    from src.validators.godot4_world import validate_world, ValidationResult

    result = validate_world(world_dict, prev_boss_hp=500)
    if not result.passed:
        print(result.report())
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Allowed key sets — no invented keys permitted
# ---------------------------------------------------------------------------

_ALLOWED_WORLD_KEYS = frozenset({
    "id", "name_display", "background_key", "music_key",
    "scroll_limit_px", "camera_y", "player_spawn", "lanes",
    "waves", "boss", "props", "scenario_ads", "dialogues_pool",
    "art_direction", "next_world",
})
_REQUIRED_WORLD_KEYS = _ALLOWED_WORLD_KEYS - {"next_world"}
_ALLOWED_WAVE_KEYS   = frozenset({"id", "trigger_x", "lock_camera", "intro", "enemies"})
_ALLOWED_ENEMY_KEYS  = frozenset({"type", "count", "x", "lane"})
_ALLOWED_PROP_KEYS   = frozenset({"type", "x", "y_lane", "throwable", "destructible"})
_ALLOWED_AD_KEYS     = frozenset({"type", "x", "text", "subtext"})
_ALLOWED_DLG_KEYS    = frozenset({"id", "speaker", "text", "trigger"})
_ALLOWED_BOSS_KEYS   = frozenset({"type", "name", "intro_dialogue", "defeat_dialogue"})

_VALID_SPEAKERS  = frozenset({"player_1", "player_2", "enemy", "boss"})
_VALID_TRIGGERS  = frozenset({
    "spawn", "combo_3", "hit", "low_health",
    "boss_spawn", "boss_phase2", "boss_defeat",
})
_VALID_PROP_TYPES = frozenset({"lamppost", "dumpster", "street_food", "cola_queue"})
_VALID_AD_TYPES   = frozenset({"billboard", "graffiti"})
_ART_DIRECTION_KEYS = frozenset({
    "bg_far_1", "bg_far_2", "bg_far_3", "bg_far_4", "bg_far_5", "bg_far_6",
    "building_01", "building_02", "building_03", "building_04", "building_05",
    "building_06", "building_07", "building_08", "building_09", "building_10",
    "building_11", "sidewalk", "ground", "wall_color",
})


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.passed = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def report(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"Validation: {status}"]
        lines += [f"  [ERROR] {e}" for e in self.errors]
        lines += [f"  [WARN ] {w}" for w in self.warnings]
        if not self.errors and not self.warnings:
            lines.append("  All checks passed.")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_keys(
    obj: dict,
    allowed: frozenset,
    label: str,
    result: ValidationResult,
) -> None:
    extra = set(obj.keys()) - allowed
    if extra:
        result.fail(f"{label} has unknown keys: {sorted(extra)}")


# ---------------------------------------------------------------------------
# Public validator
# ---------------------------------------------------------------------------

def validate_world(world: dict[str, Any], prev_boss_hp: int = 500) -> ValidationResult:
    """Validate *world* against the Barrio Bravo schema.

    Args:
        world:        The world dict (e.g. parsed from agent output).
        prev_boss_hp: HP of the boss in the preceding world, used to warn
                      about expected HP scaling.  Defaults to 500 (World01).

    Returns:
        A :class:`ValidationResult`.  ``result.passed`` is ``False`` if any
        hard rule is violated; warnings are informational only.
    """
    result = ValidationResult()

    # 1. Required top-level keys
    missing = _REQUIRED_WORLD_KEYS - set(world.keys())
    if missing:
        result.fail(f"Missing required keys: {sorted(missing)}")

    # 2. No invented top-level keys
    _check_keys(world, _ALLOWED_WORLD_KEYS, "world", result)

    # 3. Non-empty strings
    if not world.get("name_display", "").strip():
        result.fail("name_display is empty.")
    if not world.get("music_key", "").strip():
        result.fail("music_key is empty.")

    # 4. player_spawn lane ranges
    spawn = world.get("player_spawn", {})
    for key in ("p1", "p2"):
        y = spawn.get(key, {}).get("y_lane", -1)
        if not (0.0 <= y <= 1.0):
            result.fail(f"player_spawn.{key}.y_lane={y} is not in [0.0, 1.0].")

    # 5. Waves (min 2, 400px gap, valid intro speakers, enemy lanes in range)
    waves = world.get("waves", [])
    if len(waves) < 2:
        result.fail(f"Need at least 2 waves (1 combat + boss), got {len(waves)}.")
    prev_trigger = -9999.0
    combat_wave_count = 0
    for w in waves:
        _check_keys(w, _ALLOWED_WAVE_KEYS, f"wave '{w.get('id')}'", result)
        trigger = float(w.get("trigger_x", 0.0))
        gap = trigger - prev_trigger
        if prev_trigger >= 0 and gap < 400:
            result.fail(
                f"Wave '{w.get('id')}' trigger_x gap is {gap:.0f}px (minimum 400px)."
            )
        prev_trigger = trigger
        if not str(w.get("id", "")).endswith("boss"):
            combat_wave_count += 1
        intro = w.get("intro", [])
        if not isinstance(intro, list):
            result.fail(f"Wave '{w.get('id')}' intro must be a list.")
        else:
            for li, line in enumerate(intro):
                if line.get("speaker") not in _VALID_SPEAKERS:
                    result.fail(
                        f"Wave '{w.get('id')}' intro[{li}] invalid speaker."
                    )
                if not str(line.get("text", "")).strip():
                    result.fail(
                        f"Wave '{w.get('id')}' intro[{li}] has empty text."
                    )
        for enemy in w.get("enemies", []):
            _check_keys(enemy, _ALLOWED_ENEMY_KEYS, f"enemy in wave '{w.get('id')}'", result)
            lane = enemy.get("lane", -1.0)
            if not (0.0 <= lane <= 1.0):
                result.fail(
                    f"Enemy lane={lane} in wave '{w.get('id')}' is not in [0.0, 1.0]."
                )

    # 6. Props — at least 1 street_food per 2 combat waves
    props = world.get("props", [])
    street_food = sum(1 for p in props if p.get("type") == "street_food")
    min_food = max(1, combat_wave_count // 2)
    if street_food < min_food:
        result.fail(
            f"Need {min_food} street_food prop(s) for {combat_wave_count} combat "
            f"waves, found {street_food}."
        )
    for p in props:
        _check_keys(p, _ALLOWED_PROP_KEYS, "prop", result)
        if p.get("type") not in _VALID_PROP_TYPES:
            result.fail(f"Unknown prop type: '{p.get('type')}'.")
        if not (0.0 <= p.get("y_lane", -1.0) <= 1.0):
            result.fail(f"Prop y_lane={p.get('y_lane')} not in [0.0, 1.0].")

    # 7. Scenario ads — minimum 4, valid types, non-empty text
    ads = world.get("scenario_ads", [])
    if len(ads) < 4:
        result.fail(f"Need at least 4 scenario_ads, got {len(ads)}.")
    for ad in ads:
        _check_keys(ad, _ALLOWED_AD_KEYS, "scenario_ad", result)
        if ad.get("type") not in _VALID_AD_TYPES:
            result.fail(f"Unknown scenario_ad type: '{ad.get('type')}'.")
        if not str(ad.get("text", "")).strip():
            result.fail("A scenario_ad has empty text.")

    # 8. Dialogues — min 11, no duplicate ids, valid speakers and triggers
    dialogues = world.get("dialogues_pool", [])
    if len(dialogues) < 11:
        result.warn(f"Expected at least 11 dialogue entries, found {len(dialogues)}.")
    seen_ids: set[str] = set()
    for dlg in dialogues:
        _check_keys(dlg, _ALLOWED_DLG_KEYS, f"dialogue '{dlg.get('id')}'", result)
        did = str(dlg.get("id", ""))
        if did in seen_ids:
            result.fail(f"Duplicate dialogue id: '{did}'.")
        seen_ids.add(did)
        if dlg.get("speaker") not in _VALID_SPEAKERS:
            result.fail(
                f"Dialogue '{did}' has invalid speaker: '{dlg.get('speaker')}'."
            )
        if dlg.get("trigger") not in _VALID_TRIGGERS:
            result.fail(
                f"Dialogue '{did}' has invalid trigger: '{dlg.get('trigger')}'."
            )

    # 9. Boss block
    boss = world.get("boss", {})
    _check_keys(boss, _ALLOWED_BOSS_KEYS, "boss", result)
    if not str(boss.get("name", "")).strip():
        result.fail("boss.name is empty.")

    # 10. Boss HP scaling reminder (informational warning only)
    expected_min = int(prev_boss_hp * 1.15)
    expected_max = int(prev_boss_hp * 1.35)
    result.warn(
        f"Set enemies[boss_type].health to [{expected_min}–{expected_max}] "
        f"(15–35% above previous boss HP={prev_boss_hp})."
    )

    # 11. Art direction — exactly the 20 required keys, all non-empty strings
    art = world.get("art_direction", {})
    if not art:
        result.fail("art_direction is missing or empty.")
    else:
        missing_art = _ART_DIRECTION_KEYS - set(art.keys())
        if missing_art:
            result.fail(f"art_direction missing keys: {sorted(missing_art)}")
        extra_art = set(art.keys()) - _ART_DIRECTION_KEYS
        if extra_art:
            result.fail(f"art_direction has unknown keys: {sorted(extra_art)}")
        for key in _ART_DIRECTION_KEYS:
            val = art.get(key, "")
            if not isinstance(val, str) or not val.strip():
                result.fail(f"art_direction.{key} is empty or not a string.")

    return result
