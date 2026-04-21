"""Merge an approved Barrio Bravo world JSON block into data/levels_fallback.json.

Steps
-----
1. Backup the original file to ``levels_fallback.backup.json``.
2. Distribute ``scenario_ads[].x`` evenly (agents omit x — we assign it here).
3. Set ``next_world`` on the current last world to point to the new one.
4. Append the new world to the ``worlds[]`` array.
5. Update ``meta.last_updated``.
6. Write atomically (write to ``.tmp``, then rename).

Usage::

    from src.mergers.godot4_world import merge_world
    merge_world(levels_path, world_dict)
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import date
from pathlib import Path
from typing import Any


def _assign_ad_positions(world: dict[str, Any]) -> None:
    """Distribute ``scenario_ads`` evenly across ``scroll_limit_px``."""
    ads: list[dict[str, Any]] = world.get("scenario_ads", [])
    if not ads:
        return
    scroll: int = world.get("scroll_limit_px", 3096)
    step: float = scroll / (len(ads) + 1)
    for i, ad in enumerate(ads):
        ad["x"] = round(step * (i + 1), 1)


def merge_world(levels_path: Path, new_world: dict[str, Any]) -> None:
    """Merge *new_world* into ``levels_fallback.json`` at *levels_path*.

    Args:
        levels_path: Absolute path to ``{project_path}/data/levels_fallback.json``.
        new_world:   The validated and approved world dict.  Must not contain
                     the ``_meta_boss_hp`` key (strip it before calling).

    Raises:
        FileNotFoundError: If *levels_path* does not exist.
        Exception:         Any I/O error during the atomic write; the original
                           file is left untouched in that case.
    """
    if not levels_path.exists():
        raise FileNotFoundError(f"levels_fallback.json not found at: {levels_path}")

    with levels_path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)

    # Backup before touching anything.
    backup_path = levels_path.with_name("levels_fallback.backup.json")
    shutil.copy2(levels_path, backup_path)

    # Assign x positions to ads (agents omit x; we distribute evenly).
    _assign_ad_positions(new_world)

    # Chain next_world on the previous last world.
    worlds: list[dict[str, Any]] = data.get("worlds", [])
    if worlds:
        worlds[-1]["next_world"] = new_world["id"]

    # Append and update meta.
    worlds.append(new_world)
    data["worlds"] = worlds
    data.setdefault("meta", {})["last_updated"] = date.today().isoformat()

    # Atomic write: write to .tmp, then rename over the target.
    tmp_path = levels_path.with_suffix(".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, levels_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    print(f"  Backup : {backup_path}")
    print(f"  Merged : {new_world['id']} → {levels_path}")
