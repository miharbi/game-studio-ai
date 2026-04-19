"""FastAPI application — Game Studio AI web UI."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.routes import plans, gates, sprites as sprite_routes, editors, settings, docs

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

_TAGS_METADATA = [
    {
        "name": "Runs",
        "description": "Start plan runs, stream live agent output via SSE, and resolve gate checkpoints.",
    },
    {
        "name": "Sprites",
        "description": "Approve or reject generated sprite images in the pending review queue.",
    },
    {
        "name": "Agents",
        "description": "CRUD operations for agent persona files stored under `agents/`.",
    },
    {
        "name": "Plans",
        "description": "CRUD operations for plan template YAML files stored under `plans/templates/`.",
    },
    {
        "name": "Config",
        "description": "Read and write `config/models.yaml` (model routing) and `config/.env` (API keys).",
    },
    {
        "name": "Engines",
        "description": "CRUD operations for engine context YAML files stored under `config/engines/`.",
    },
]

app = FastAPI(
    title="Game Studio AI",
    version="0.1.0",
    description=(
        "REST API for the Game Studio AI multi-agent orchestrator. "
        "Interactive docs are available at **/docs** (Swagger UI) and **/redoc** (ReDoc). "
        "HTML UI endpoints are excluded from this schema — only JSON endpoints are listed."
    ),
    openapi_tags=_TAGS_METADATA,
)

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
app.include_router(docs.router)
