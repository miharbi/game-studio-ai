"""Tier → model router.

Reads config/models.yaml; environment variables override individual tiers.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH: Path = Path(__file__).resolve().parents[2] / "config" / "models.yaml"
_config: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    global _config
    if _config is None:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def get_model(tier: int, engine: str | None = None) -> str:
    """Return the model ID for a given agent tier and optional engine."""
    cfg = _load_config()

    # Environment variable overrides take priority
    env_key = f"TIER{tier}_MODEL"
    if env_val := os.environ.get(env_key):
        return env_val

    # Engine-specific override
    if engine:
        overrides: dict[str, Any] = cfg.get("engine_overrides", {}).get(engine, {})
        tier_key = f"tier{tier}"
        if tier_key in overrides:
            return str(overrides[tier_key])

    # Default tier model
    tier_cfg: dict[str, Any] = cfg.get("tiers", {}).get(tier, {})
    return str(tier_cfg.get("model", "openai/gpt-4o-mini"))


def get_sprite_config() -> dict[str, Any]:
    """Return the sprite generation config block."""
    return dict(_load_config().get("sprites", {}))
