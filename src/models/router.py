"""Tier → model router.

Reads config/models.yaml; environment variables override individual tiers.
Thread-safe config loading. Provider catalog with context-window awareness.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH: Path = Path(__file__).resolve().parents[2] / "config" / "models.yaml"
_config: dict[str, Any] | None = None
_config_lock = threading.Lock()


def invalidate_config_cache() -> None:
    """Clear the in-memory config cache so the next call re-reads models.yaml."""
    global _config
    with _config_lock:
        _config = None


# Conservative fallback when model info is unavailable.
_DEFAULT_CONTEXT_WINDOW: int = 8192


def _load_config() -> dict[str, Any]:
    global _config
    if _config is not None:
        return _config
    with _config_lock:
        if _config is not None:  # double-check after acquiring lock
            return _config
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


def get_context_window(model: str) -> int:
    """Return the context window size (in tokens) for a model.

    Checks the local providers catalog in models.yaml first,
    then falls back to litellm.get_model_info(), then a safe default.
    """
    cfg = _load_config()
    # Search the local providers catalog
    for provider in cfg.get("providers", {}).values():
        for m in provider.get("models", []):
            if m.get("id") == model:
                return int(m["context_window"])

    # Try litellm's model info registry
    try:
        import litellm
        info = litellm.get_model_info(model)
        if info and "max_input_tokens" in info:
            return int(info["max_input_tokens"])
    except Exception:
        pass

    return _DEFAULT_CONTEXT_WINDOW


def list_providers() -> dict[str, Any]:
    """Return the providers catalog from models.yaml."""
    return dict(_load_config().get("providers", {}))
