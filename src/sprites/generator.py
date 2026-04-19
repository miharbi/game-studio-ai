"""Sprite generator — provider-agnostic image generation.

Providers:
  stub             — writes a placeholder PNG (no API call)
  openai           — DALL-E 3 via openai SDK
  stable_diffusion — SD WebUI REST API (local or remote)
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from src.sprites.spec_builder import SpriteSpec

_OUTPUT_DIR: Path = Path(__file__).resolve().parents[2] / "output" / "sprites"


def generate(spec: SpriteSpec, provider: str | None = None) -> Path:
    """
    Generate a sprite image for the given SpriteSpec.
    Returns the path to the generated PNG file.
    """
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chosen_provider = provider or os.environ.get("SPRITE_PROVIDER", "stub")

    if chosen_provider == "openai":
        return _generate_openai(spec)
    if chosen_provider == "stable_diffusion":
        return _generate_sd(spec)
    return _generate_stub(spec)


def _generate_stub(spec: SpriteSpec) -> Path:
    """Write a placeholder PNG (solid colour block) for testing without API calls."""
    try:
        from PIL import Image, ImageDraw  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("Pillow not installed. Run: pip install Pillow") from exc

    img = Image.new("RGBA", (spec.width, spec.height), (80, 120, 200, 255))
    draw = ImageDraw.Draw(img)
    draw.text((4, 4), spec.name[:12], fill=(255, 255, 255, 255))

    out = _output_path(spec)
    img.save(out, "PNG")
    return out


def _generate_openai(spec: SpriteSpec) -> Path:
    """Generate via DALL-E 3. Requires OPENAI_API_KEY env var."""
    try:
        from openai import OpenAI  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("openai not installed. Run: pip install openai") from exc

    client = OpenAI()
    response = client.images.generate(
        model="dall-e-3",
        prompt=spec.prompt,
        size="1024x1024",
        response_format="b64_json",
        n=1,
    )
    img_data: str = response.data[0].b64_json  # type: ignore[union-attr]
    raw: bytes = base64.b64decode(img_data)

    out = _output_path(spec)
    out.write_bytes(raw)
    return out


def _generate_sd(spec: SpriteSpec) -> Path:
    """Generate via Stable Diffusion WebUI REST API."""
    try:
        import httpx  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("httpx not installed. Run: pip install httpx") from exc

    sd_url = os.environ.get("SD_API_URL", "http://localhost:7860")
    payload: dict[str, Any] = {
        "prompt": spec.prompt,
        "negative_prompt": spec.negative_prompt,
        "width": spec.width,
        "height": spec.height,
        "steps": 20,
        "cfg_scale": 7,
        "batch_size": 1,
    }
    response = httpx.post(f"{sd_url}/sdapi/v1/txt2img", json=payload, timeout=120)
    response.raise_for_status()
    img_b64: str = response.json()["images"][0]
    raw = base64.b64decode(img_b64)

    out = _output_path(spec)
    out.write_bytes(raw)
    return out


def _output_path(spec: SpriteSpec) -> Path:
    safe_name = spec.name.replace("/", "_").replace(" ", "_")
    return _OUTPUT_DIR / f"{safe_name}.png"
