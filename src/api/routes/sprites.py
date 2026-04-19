"""Sprite gallery API routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

_SPRITES_DIR = Path(__file__).resolve().parents[3] / "output" / "sprites"
_APPROVED_DIR = Path(__file__).resolve().parents[3] / "output" / "approved"


@router.get("/sprites", response_class=HTMLResponse)
async def sprite_gallery(request: Request) -> HTMLResponse:
    images = sorted(_SPRITES_DIR.glob("*.png"))
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="sprites.html",
        context={"images": [img.name for img in images]},
    )


@router.post("/sprites/{name}/approve")
async def approve_sprite(name: str) -> dict[str, str]:
    src = _SPRITES_DIR / name
    if not src.exists():
        raise HTTPException(404, f"Sprite '{name}' not found.")
    _APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    dst = _APPROVED_DIR / name
    src.rename(dst)
    return {"status": "approved", "path": str(dst)}


@router.post("/sprites/{name}/reject")
async def reject_sprite(name: str) -> dict[str, str]:
    src = _SPRITES_DIR / name
    if not src.exists():
        raise HTTPException(404, f"Sprite '{name}' not found.")
    src.unlink()
    return {"status": "rejected", "name": name}
