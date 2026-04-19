"""Loads agent definitions from agents/tierN/*.md files.

Each file has YAML frontmatter followed by the system prompt body:

    ---
    name: level_designer
    tier: 3
    reports_to: game_designer
    domain: level design
    ---
    You are a Level Designer...
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.DOTALL)


@dataclass
class AgentDefinition:
    name: str
    tier: int
    model_override: str | None
    reports_to: str | None
    domain: str
    system_prompt: str
    source_file: Path


class AgentLoader:
    """Scans agents/ directory and parses all agent definition files."""

    def __init__(self, agents_dir: Path) -> None:
        self._dir = agents_dir
        self._cache: dict[str, AgentDefinition] = {}

    def load(self, name: str) -> AgentDefinition:
        """Load a specific agent by name."""
        if name in self._cache:
            return self._cache[name]
        for path in self._dir.rglob("*.md"):
            agent = _parse_agent_file(path)
            self._cache[agent.name] = agent
            if agent.name == name:
                return agent
        raise FileNotFoundError(f"Agent '{name}' not found in {self._dir}")

    def list_all(self) -> dict[int, list[AgentDefinition]]:
        """Return all agents grouped by tier."""
        result: dict[int, list[AgentDefinition]] = {}
        for path in sorted(self._dir.rglob("*.md")):
            agent = _parse_agent_file(path)
            self._cache[agent.name] = agent
            result.setdefault(agent.tier, []).append(agent)
        return dict(sorted(result.items()))


def _parse_agent_file(path: Path) -> AgentDefinition:
    """Parse a single agent markdown file."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"Agent file {path} is missing YAML frontmatter (--- block)")

    meta: dict[str, Any] = yaml.safe_load(match.group(1))
    system_prompt: str = match.group(2).strip()

    return AgentDefinition(
        name=meta["name"],
        tier=int(meta["tier"]),
        model_override=meta.get("model_override"),
        reports_to=meta.get("reports_to"),
        domain=meta.get("domain", ""),
        system_prompt=system_prompt,
        source_file=path,
    )
