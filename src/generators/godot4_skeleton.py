"""Deterministically compute the structural skeleton for the next Barrio Bravo world.

All gameplay numbers are derived from the previous world — agents fill in
narrative/creative content (name, dialogue, art_direction, scenario_ads,
wave intro lines) on top of this skeleton.

Difficulty baseline (World01)
-----------------------------
  scroll_limit_px : 3096   boss_hp : 500
  wave_count      : 4      combat_waves : 3   total_enemies : 5

Usage::

    import json
    from pathlib import Path
    from src.generators.godot4_skeleton import extract_prev_stats, compute_skeleton

    with open(project_path / "data" / "levels_fallback.json") as fh:
        data = json.load(fh)

    prev  = extract_prev_stats(data)
    skel  = compute_skeleton(prev, boss_type="boss_2")

    boss_hp = skel.pop("_meta_boss_hp")   # strip before validation / merge
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

ENEMY_PROGRESSION = ["enemy_1", "enemy_2", "enemy_3"]
PROP_CYCLE = [
    {"type": "lamppost"},
    {"type": "dumpster", "throwable": True},
    {"type": "cola_queue"},
    {"type": "dumpster", "throwable": True},
    {"type": "lamppost"},
]


# ---------------------------------------------------------------------------
# Previous-world stats
# ---------------------------------------------------------------------------

@dataclass
class PrevWorldStats:
    world_num: int
    scroll_limit_px: int
    boss_hp: int
    wave_count: int
    combat_wave_count: int
    camera_y: float
    lanes: dict[str, Any]


def extract_prev_stats(data: dict[str, Any]) -> PrevWorldStats:
    """Parse ``levels_fallback.json`` and return stats from the last world.

    Args:
        data: Parsed JSON content of ``levels_fallback.json``.

    Raises:
        ValueError: If the file contains no worlds.
    """
    worlds = data.get("worlds", [])
    if not worlds:
        raise ValueError("levels_fallback.json has no worlds.")
    last = worlds[-1]
    boss_type = last.get("boss", {}).get("type", "boss_1")
    # HP lives in the top-level enemies table; fall back to 500 if missing.
    boss_hp = (
        data.get("enemies", {})
        .get(boss_type, {})
        .get("health", 500)
    )
    waves = last.get("waves", [])
    combat = sum(1 for w in waves if not str(w.get("id", "")).endswith("boss"))
    return PrevWorldStats(
        world_num=len(worlds),
        scroll_limit_px=last.get("scroll_limit_px", 3096),
        boss_hp=boss_hp,
        wave_count=len(waves),
        combat_wave_count=combat,
        camera_y=last.get("camera_y", 475.0),
        lanes=last.get("lanes", {
            "y_top": 530, "y_bottom": 575,
            "depth_scale_min": 0.7, "depth_scale_max": 1.0,
        }),
    )


# ---------------------------------------------------------------------------
# Scaling helpers
# ---------------------------------------------------------------------------

def _next_scroll_limit(prev: int) -> int:
    return prev + 400


def _next_boss_hp(prev_hp: int) -> int:
    return int(prev_hp * 1.25)


def _next_combat_wave_count(prev_combat: int) -> int:
    return min(prev_combat + random.randint(0, 1), 6)


def _enemy_mix(wave_index: int, world_num: int) -> list[str]:
    """Return enemy type list for a wave slot.

    Harder enemies appear sooner in later worlds.
    """
    count = min(2 + wave_index + (world_num - 2), 5)
    hardness = min((world_num - 2) * 0.15 + wave_index * 0.1, 0.9)
    result: list[str] = []
    for _ in range(count):
        r = random.random()
        if r > hardness + 0.2:
            result.append("enemy_1")
        elif r > hardness - 0.2:
            result.append("enemy_2")
        else:
            result.append("enemy_3")
    return result


def _build_waves(
    combat_count: int,
    world_num: int,
    boss_type: str,
    scroll_limit: int,
) -> list[dict[str, Any]]:
    waves: list[dict[str, Any]] = []
    usable = scroll_limit - 600
    spacing = max(400, min(600, usable // (combat_count + 1)))
    current_x = spacing
    for i in range(combat_count):
        enemies = _enemy_mix(i, world_num)
        waves.append({
            "id": f"wave_{i + 1:02d}",
            "trigger_x": float(current_x),
            "lock_camera": True,
            "intro": [],
            "enemies": [
                {
                    "type": t,
                    "count": 1,
                    "x": float(current_x + 70 + j * 50),
                    "lane": round(0.3 + (j % 3) * 0.2, 1),
                }
                for j, t in enumerate(enemies)
            ],
        })
        current_x += spacing
    boss_x = float(scroll_limit - 400)
    waves.append({
        "id": "wave_boss",
        "trigger_x": boss_x,
        "lock_camera": True,
        "intro": [],
        "enemies": [{"type": boss_type, "count": 1, "x": boss_x + 70.0, "lane": 0.5}],
    })
    return waves


def _build_props(combat_count: int, scroll_limit: int) -> list[dict[str, Any]]:
    total = 10
    street_food_count = max(1, combat_count // 2)
    step = scroll_limit / (total + 1)
    lanes = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    food_positions = set(range(2, total, max(1, total // street_food_count)))
    props: list[dict[str, Any]] = []
    for i in range(total):
        x = round(step * (i + 1), 1)
        y = lanes[i % len(lanes)]
        if i in food_positions:
            props.append({"type": "street_food", "x": x, "y_lane": y, "destructible": True})
        else:
            entry = PROP_CYCLE[i % len(PROP_CYCLE)].copy()
            entry.update({"x": x, "y_lane": y})
            props.append(entry)
    return props


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_skeleton(
    prev: PrevWorldStats,
    *,
    boss_type: str = "boss_1",
    seed: int | None = None,
) -> dict[str, Any]:
    """Return a partial world dict with all structural fields pre-filled.

    The ``level_designer`` agent fills: ``name_display``, ``music_key``,
    ``boss.name``, ``boss.intro_dialogue``, ``boss.defeat_dialogue``,
    ``dialogues_pool``, ``scenario_ads``, ``art_direction``, and wave intro lines.

    The ``_meta_boss_hp`` key **must** be stripped before calling
    :func:`src.validators.godot4_world.validate_world` or
    :func:`src.mergers.godot4_world.merge_world`.  Use its value to update
    ``enemies[boss_type].health`` in ``levels_fallback.json``.

    Args:
        prev:      Stats extracted from the previous world via
                   :func:`extract_prev_stats`.
        boss_type: Enemy type key for the boss (e.g. ``"boss_2"``).
        seed:      Optional random seed for deterministic output.

    Returns:
        A partial world dict.
    """
    if seed is not None:
        random.seed(seed)

    new_num = prev.world_num + 1
    scroll_limit = _next_scroll_limit(prev.scroll_limit_px)
    boss_hp = _next_boss_hp(prev.boss_hp)
    combat_count = _next_combat_wave_count(prev.combat_wave_count)

    return {
        "id": f"World{new_num:02d}",
        "background_key": f"World{new_num:02d}Bg",
        "scroll_limit_px": scroll_limit,
        "camera_y": prev.camera_y,
        "lanes": prev.lanes,
        "player_spawn": {
            "p1": {"x": 100.0, "y_lane": 0.5},
            "p2": {"x": 150.0, "y_lane": 0.5},
        },
        "waves": _build_waves(combat_count, new_num, boss_type, scroll_limit),
        "boss": {
            "type": boss_type,
            "name": "",
            "intro_dialogue": "",
            "defeat_dialogue": "",
        },
        "props": _build_props(combat_count, scroll_limit),
        # Strip this key before validation and merge; apply value to
        # enemies[boss_type].health in levels_fallback.json.
        "_meta_boss_hp": boss_hp,
    }
