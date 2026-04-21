"""Per-agent game spec context injection.

build_agent_context(agent_name, engine_ctx) extracts the sections of
game_spec.json and level_template.json that are relevant to the given
agent and returns them as a formatted string ready to be appended to
the agent's system prompt.

Section routing table
---------------------
art_director    : meta + art_style + characters + vfx + sample_assets
audio_director  : meta + audio
technical_artist: meta + art_style + characters + vfx
level_designer  : meta + world_authoring  (+level_template.json)
world_builder   : meta + art_style + world_authoring  (+level_template.json)
writer          : meta + characters + audio.sfx
All others      : meta only
"""
from __future__ import annotations

import json
from typing import Any

# Keys from game_spec.json injected per agent role.
_AGENT_SPEC_SECTIONS: dict[str, list[str]] = {
    "art_director":     ["meta", "art_style", "characters", "vfx", "sample_assets"],
    "audio_director":   ["meta", "audio"],
    "technical_artist": ["meta", "art_style", "characters", "vfx"],
    "level_designer":   ["meta", "world_authoring"],
    "world_builder":    ["meta", "art_style", "world_authoring"],
    "writer":           ["meta", "characters", "audio"],
}

# Agents that also receive the full level_template.json.
_LEVEL_TEMPLATE_AGENTS: frozenset[str] = frozenset({"level_designer", "world_builder"})


def build_agent_context(agent_name: str, engine_ctx: dict[str, Any]) -> str:
    """Build the spec context string for *agent_name*.

    Args:
        agent_name: The agent's ``name`` field (e.g. ``"art_director"``).
        engine_ctx: The dict returned by ``src.engines.loader.load_engine_context``.

    Returns:
        A formatted string to append to the agent's system prompt, or an
        empty string when no spec files are present in *engine_ctx*.
    """
    spec_files: dict[str, Any] = engine_ctx.get("spec_files", {})
    if not spec_files:
        return ""

    game_spec: dict[str, Any] = spec_files.get("data/game_spec.json", {})
    level_template: dict[str, Any] = spec_files.get("data/level_template.json", {})

    parts: list[str] = []

    if game_spec:
        keys = _AGENT_SPEC_SECTIONS.get(agent_name, ["meta"])
        filtered: dict[str, Any] = {k: game_spec[k] for k in keys if k in game_spec}
        if filtered:
            parts.append(
                "## Game Spec Context (from data/game_spec.json)\n\n"
                + json.dumps(filtered, ensure_ascii=False, indent=2)
            )

    if level_template and agent_name in _LEVEL_TEMPLATE_AGENTS:
        parts.append(
            "## Level Template (from data/level_template.json)\n\n"
            + json.dumps(level_template, ensure_ascii=False, indent=2)
        )

    return "\n\n".join(parts)
