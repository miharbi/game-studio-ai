"""Settings API routes — project path and detection."""
from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter()

_CONFIG_DIR: Path = Path(__file__).resolve().parents[3] / "config"
_SETTINGS_PATH: Path = _CONFIG_DIR / "settings.yaml"
_ENGINES_DIR: Path = _CONFIG_DIR / "engines"


class SettingsUpdate(BaseModel):
    project_path: str = ""


def _load_settings() -> dict:
    """Load settings.yaml or return defaults."""
    if _SETTINGS_PATH.exists():
        try:
            data = yaml.safe_load(_SETTINGS_PATH.read_text()) or {}
            return {"project_path": data.get("project_path", "")}
        except Exception:
            pass
    return {"project_path": ""}


def _detect_engine(project_path: str) -> dict | None:
    """Try to detect a game engine from the project directory."""
    if not project_path:
        return None
    p = Path(project_path)
    if not p.is_dir():
        return None
    for engine_file in sorted(_ENGINES_DIR.glob("*.yaml")):
        try:
            cfg = yaml.safe_load(engine_file.read_text()) or {}
            detect_files = cfg.get("detect_files", [])
            for df in detect_files:
                if (p / df).exists():
                    return {
                        "id": cfg.get("id", engine_file.stem),
                        "name": cfg.get("name", engine_file.stem),
                        "matched": df,
                    }
        except Exception:
            continue
    return None


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    settings = _load_settings()
    detected = _detect_engine(settings["project_path"])
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"settings": settings, "detected_engine": detected},
    )


@router.put("/settings")
async def settings_update(body: SettingsUpdate) -> dict:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {"project_path": body.project_path.strip()}
    _SETTINGS_PATH.write_text(yaml.dump(data, default_flow_style=False))
    detected = _detect_engine(data["project_path"])
    return {"status": "saved", "detected_engine": detected}
