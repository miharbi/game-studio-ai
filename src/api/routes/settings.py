"""Settings routes — redirect to /edit/config (consolidated)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/settings")
async def settings_redirect_get() -> RedirectResponse:
    return RedirectResponse(url="/edit/config", status_code=301)


@router.put("/settings")
async def settings_redirect_put() -> RedirectResponse:
    return RedirectResponse(url="/edit/config", status_code=301)
