"""Sprite gallery API routes."""
from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Sprites"])

_SPRITES_DIR = Path(__file__).resolve().parents[3] / "output" / "sprites"
_APPROVED_DIR = Path(__file__).resolve().parents[3] / "output" / "approved"
_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "models.yaml"


def _get_sprite_config() -> dict:
    """Read the sprites section from models.yaml, with safe defaults."""
    defaults = {"provider": "stub", "model": "dall-e-3", "image_size": "1024x1024"}
    if not _CONFIG_PATH.exists():
        return defaults
    try:
        data = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
        cfg = data.get("sprites", {})
        return {k: cfg.get(k, v) for k, v in defaults.items()}
    except Exception:
        return defaults


@router.get("/sprites", response_class=HTMLResponse, include_in_schema=False)
async def sprite_gallery(request: Request) -> HTMLResponse:
    pending = sorted(_SPRITES_DIR.glob("*.png"))
    approved = sorted(_APPROVED_DIR.glob("*.png")) if _APPROVED_DIR.exists() else []
    sprite_cfg = _get_sprite_config()
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="sprites.html",
        context={
            "images": [img.name for img in pending],
            "approved_count": len(approved),
            "sprite_config": sprite_cfg,
        },
    )


@router.post(
    "/sprites/{name}/approve",
    summary="Approve a pending sprite",
    response_description="Approval status and destination path",
)
async def approve_sprite(name: str) -> dict[str, str]:
    """Move `name` from the pending sprites directory to `output/approved/`."""
    src = _SPRITES_DIR / name
    if not src.exists():
        raise HTTPException(404, f"Sprite '{name}' not found.")
    _APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    dst = _APPROVED_DIR / name
    src.rename(dst)
    return {"status": "approved", "path": str(dst)}


@router.post(
    "/sprites/{name}/reject",
    summary="Reject and delete a pending sprite",
    response_description="Rejection status",
)
async def reject_sprite(name: str) -> dict[str, str]:
    """Permanently delete `name` from the pending sprites directory."""
    src = _SPRITES_DIR / name
    if not src.exists():
        raise HTTPException(404, f"Sprite '{name}' not found.")
    src.unlink()
    return {"status": "rejected", "name": name}
