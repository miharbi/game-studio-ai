"""Sprite post-processor.

Resizes generated images to engine-specific target dimensions,
assembles sprite sheets, and writes engine metadata files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.sprites.spec_builder import SpriteSpec
from src.engines.detect import load_engine_config


def post_process(image_path: Path, spec: SpriteSpec) -> Path:
    """
    Resize the image to spec dimensions, apply PNG optimization,
    and write engine-specific metadata alongside it.
    Returns the final image path (may be same as input).
    """
    try:
        from PIL import Image  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("Pillow not installed. Run: pip install Pillow") from exc

    with Image.open(image_path) as img:
        resized = img.resize((spec.width, spec.height), Image.LANCZOS)
        resized.save(image_path, "PNG", optimize=True)

    _write_engine_metadata(image_path, spec)
    return image_path


def _write_engine_metadata(image_path: Path, spec: SpriteSpec) -> None:
    if spec.engine == "godot4":
        _write_godot_import(image_path, spec)
    elif spec.engine == "unity":
        _write_unity_meta(image_path, spec)
    elif spec.engine == "unreal5":
        _write_unreal_metadata(image_path, spec)


def _write_godot_import(image_path: Path, spec: SpriteSpec) -> None:
    cfg = load_engine_config("godot4")
    template: str = cfg.get("sprite_output", {}).get("import_template", "")
    if not template:
        return
    import_path = image_path.with_suffix(image_path.suffix + ".import")
    import_path.write_text(template.strip() + "\n", encoding="utf-8")


def _write_unity_meta(image_path: Path, spec: SpriteSpec) -> None:
    meta_path = image_path.with_suffix(image_path.suffix + ".meta")
    meta_path.write_text(
        f"# Unity texture meta (auto-generated)\n"
        f"fileFormatVersion: 2\n"
        f"textureType: Sprite\n"
        f"pixelsPerUnit: 100\n"
        f"spriteName: {spec.name}\n",
        encoding="utf-8",
    )


def _write_unreal_metadata(image_path: Path, spec: SpriteSpec) -> None:
    meta_path = image_path.with_suffix(".uasset.json")
    import json
    data: dict[str, Any] = {
        "asset_name": spec.name,
        "compression": "TC_EditorIcon",
        "sRGB": True,
        "width": spec.width,
        "height": spec.height,
    }
    meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
