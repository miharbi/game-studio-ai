"""Engine detection and context injection.

detect(project_path) returns the engine ID string or None.
load_engine_context(engine_id) returns the agent context string from the engine YAML.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ENGINES_CONFIG_DIR: Path = (
    Path(__file__).resolve().parents[2] / "config" / "engines"
)

_DETECT_HINTS: list[tuple[str, list[str]]] = [
    ("godot4",   ["project.godot"]),
    ("unity",    ["ProjectSettings/ProjectVersion.txt"]),
    ("unreal5",  ["*.uproject"]),
]


def detect(project_path: Path) -> str | None:
    """Return engine ID for a game project directory, or None if unrecognised."""
    p = Path(project_path)
    if not p.is_dir():
        return None
    for engine_id, hints in _DETECT_HINTS:
        for hint in hints:
            if "*" in hint:
                if any(p.glob(hint)):
                    return engine_id
            elif (p / hint).exists():
                return engine_id
    return None


def load_engine_context(engine_id: str) -> str:
    """Return the agent_context string from a config/engines/<id>.yaml file."""
    cfg_path = _ENGINES_CONFIG_DIR / f"{engine_id}.yaml"
    if not cfg_path.exists():
        return ""
    data: dict[str, Any] = yaml.safe_load(cfg_path.read_text())
    return str(data.get("agent_context", "")).strip()


def load_engine_config(engine_id: str) -> dict[str, Any]:
    """Return the full engine config dict."""
    cfg_path = _ENGINES_CONFIG_DIR / f"{engine_id}.yaml"
    if not cfg_path.exists():
        return {}
    return dict(yaml.safe_load(cfg_path.read_text()))
