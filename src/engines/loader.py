"""Project-aware engine context loader.

load_engine_context(project_path) detects the engine for a game project
directory, then lazily loads any spec files declared in the engine YAML
(e.g. game_spec.json, level_template.json for Godot 4 projects).

Returns a dict with:
  engine_id    : str | None
  agent_context: str           (the agent_context string from the YAML)
  spec_files   : dict[str, Any]  (keyed by relative path, value is parsed JSON)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.engines.detect import detect, load_engine_config

logger = logging.getLogger(__name__)


def load_engine_context(project_path: Path) -> dict[str, Any]:
    """Detect engine and load spec files for *project_path*.

    Args:
        project_path: Absolute path to the root of the game project.

    Returns:
        A dict with keys ``engine_id``, ``agent_context``, and ``spec_files``.
        ``spec_files`` maps each relative path declared in the engine YAML
        ``spec_files`` list to its parsed JSON content.  Missing files are
        skipped with a warning — no exception is raised.
    """
    project_path = Path(project_path)
    engine_id = detect(project_path)

    if not engine_id:
        return {"engine_id": None, "agent_context": "", "spec_files": {}}

    engine_config = load_engine_config(engine_id)
    agent_context = str(engine_config.get("agent_context", "")).strip()

    spec_files: dict[str, Any] = {}
    for spec_rel_path in engine_config.get("spec_files", []):
        spec_abs_path = project_path / spec_rel_path
        if spec_abs_path.exists():
            try:
                with spec_abs_path.open("r", encoding="utf-8") as fh:
                    spec_files[spec_rel_path] = json.load(fh)
            except Exception as exc:
                logger.warning(
                    "game-studio-ai: failed to parse spec file %s: %s — skipping.",
                    spec_abs_path,
                    exc,
                )
        else:
            logger.warning(
                "game-studio-ai: spec file not found at %s — skipping. "
                "Some agents will have reduced context.",
                spec_abs_path,
            )

    return {
        "engine_id": engine_id,
        "agent_context": agent_context,
        "spec_files": spec_files,
    }
