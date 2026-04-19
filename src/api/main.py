"""FastAPI application — Game Studio AI web UI."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.routes import plans, gates, sprites as sprite_routes, editors, settings

_BASE_DIR: Path = Path(__file__).resolve().parent


def _load_dot_env() -> None:
    """Load config/.env into os.environ at startup if it exists."""
    dot_env = _BASE_DIR.parents[1] / "config" / ".env"
    if dot_env.exists():
        for line in dot_env.read_text().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k and v:
                    os.environ.setdefault(k, v)


_load_dot_env()

app = FastAPI(title="Game Studio AI", version="0.1.0")

app.mount(
    "/static",
    StaticFiles(directory=str(_BASE_DIR / "static")),
    name="static",
)

templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))

# Expose templates to routes
app.state.templates = templates

app.include_router(plans.router)
app.include_router(gates.router)
app.include_router(sprite_routes.router)
app.include_router(editors.router)
app.include_router(settings.router)
