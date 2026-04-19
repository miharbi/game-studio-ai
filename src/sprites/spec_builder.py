"""Sprite spec builder.

Converts an art_direction dict (engine-agnostic) into detailed
image generation prompts for each layer / character.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Sprite dimension presets per engine and asset type.
_DIMENSIONS: dict[str, dict[str, tuple[int, int]]] = {
    "godot4": {
        "player":        (48, 64),
        "enemy":         (32, 48),
        "boss":          (64, 80),
        "background":    (768, 144),
        "building":      (128, 144),
        "prop":          (32, 32),
        "ui_icon":       (64, 64),
    },
    "unity": {
        "player":        (512, 512),
        "enemy":         (256, 256),
        "boss":          (512, 512),
        "background":    (2048, 512),
        "building":      (512, 512),
        "prop":          (128, 128),
        "ui_icon":       (128, 128),
    },
    "unreal5": {
        "player":        (1024, 1024),
        "enemy":         (512, 512),
        "boss":          (1024, 1024),
        "background":    (4096, 1024),
        "building":      (1024, 1024),
        "prop":          (256, 256),
        "ui_icon":       (256, 256),
    },
}

_STYLE_PREFIX = (
    "pixel art, retro arcade style, clean outlines, transparent background, "
    "vibrant colors, sharp edges, no anti-aliasing, "
)


@dataclass
class SpriteSpec:
    name: str
    asset_type: str
    prompt: str
    negative_prompt: str
    width: int
    height: int
    engine: str
    metadata: dict[str, Any]


def build_spec(
    name: str,
    asset_type: str,
    art_direction: str,
    engine: str = "godot4",
    extra_metadata: dict[str, Any] | None = None,
) -> SpriteSpec:
    """Build a SpriteSpec from an art_direction description."""
    dims = _DIMENSIONS.get(engine, _DIMENSIONS["godot4"])
    w, h = dims.get(asset_type, (64, 64))

    prompt = f"{_STYLE_PREFIX}{art_direction}, {w}x{h} pixel art sprite"

    negative = (
        "3d render, realistic, blurry, watermark, text, signature, "
        "low quality, gradient background, non-transparent background"
    )

    return SpriteSpec(
        name=name,
        asset_type=asset_type,
        prompt=prompt,
        negative_prompt=negative,
        width=w,
        height=h,
        engine=engine,
        metadata=extra_metadata or {},
    )


def build_specs_from_art_direction(
    art_direction: dict[str, str],
    engine: str = "godot4",
) -> list[SpriteSpec]:
    """
    Build a list of SpriteSpecs from an art_direction dict (e.g. from level JSON).

    Keys like 'bg_far_1', 'building_01' are auto-mapped to asset types.
    """
    specs: list[SpriteSpec] = []
    for key, description in art_direction.items():
        if not description:
            continue
        asset_type = _infer_asset_type(key)
        specs.append(build_spec(
            name=key,
            asset_type=asset_type,
            art_direction=description,
            engine=engine,
        ))
    return specs


def _infer_asset_type(key: str) -> str:
    if key.startswith("bg_"):
        return "background"
    if key.startswith("building_"):
        return "building"
    if "player" in key:
        return "player"
    if "enemy" in key or "boss" in key:
        return "enemy"
    if "ui" in key or "icon" in key:
        return "ui_icon"
    return "prop"
