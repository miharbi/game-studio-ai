"""Editor routes — in-browser CRUD for agents, plans, config & engines."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter(prefix="/edit")

_ROOT: Path = Path(__file__).resolve().parents[3]
_AGENTS_DIR: Path = _ROOT / "agents"
_PLANS_DIR: Path = _ROOT / "plans" / "templates"
_CONFIG_DIR: Path = _ROOT / "config"
_ENGINES_DIR: Path = _CONFIG_DIR / "engines"

# ── safety helpers ──────────────────────────────────────────────────────────

_SAFE_FILENAME = re.compile(r"^[a-zA-Z0-9_\-]+\.(md|yaml)$")


def _safe_name(name: str) -> str:
    """Validate and return a safe filename, or raise 422."""
    name = Path(name).name          # strip directory components
    if not _SAFE_FILENAME.match(name):
        raise HTTPException(422, f"Invalid filename: {name}")
    return name


# ── parse helpers ───────────────────────────────────────────────────────────

def _parse_agent(content: str) -> dict[str, Any]:
    """Split agent .md into frontmatter fields and body."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].lstrip("\n")
            return {**fm, "body": body}
    return {"name": "", "tier": 3, "reports_to": None, "domain": "", "body": content}


def _parse_plan(content: str) -> dict[str, Any]:
    """Parse plan YAML into structured dict."""
    data = yaml.safe_load(content) or {}
    return {
        "task": data.get("task", ""),
        "description": data.get("description", ""),
        "engine": data.get("engine"),
        "input": data.get("input", ""),
        "steps": data.get("steps", []),
    }


def _parse_config(content: str) -> dict[str, Any]:
    """Parse models.yaml into structured sections."""
    data = yaml.safe_load(content) or {}
    return {
        "tiers": data.get("tiers", {}),
        "engine_overrides": data.get("engine_overrides", {}),
        "sprites": data.get("sprites", {}),
        "providers": data.get("providers", {}),
        "raw": content,
    }


def _list_agents() -> list[dict[str, str]]:
    agents: list[dict[str, str]] = []
    for tier_dir in sorted(_AGENTS_DIR.iterdir()):
        if not tier_dir.is_dir() or not tier_dir.name.startswith("tier"):
            continue
        for f in sorted(tier_dir.glob("*.md")):
            agents.append({"tier": tier_dir.name, "file": f.name, "path": f"{tier_dir.name}/{f.name}"})
    return agents


def _list_all_models() -> list[str]:
    """Return flat list of all model IDs from providers catalog."""
    path = _CONFIG_DIR / "models.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    models: list[str] = []
    for prov in (data.get("providers") or {}).values():
        for m in prov.get("models", []):
            models.append(m["id"])
    return models


def _list_schema_types() -> list[str]:
    return ["json", "level_json", "sprite_spec", "code_block", "feature_design"]


# ── build helpers ───────────────────────────────────────────────────────────

def _build_agent_md(body: "AgentBody") -> str:
    """Reconstruct .md file from structured agent data."""
    fm: dict[str, Any] = {
        "name": body.name,
        "tier": body.tier,
        "reports_to": body.reports_to,
        "domain": body.domain,
    }
    if body.model_override:
        fm["model_override"] = body.model_override
    frontmatter = yaml.dump(fm, default_flow_style=False, sort_keys=False).rstrip()
    return f"---\n{frontmatter}\n---\n{body.body}"


def _build_plan_yaml(body: "PlanBody") -> str:
    """Reconstruct YAML from structured plan data."""
    steps = []
    for s in body.steps:
        step: dict[str, Any] = {
            "id": s.id,
            "agent": s.agent,
            "tier": s.tier,
            "action": s.action,
        }
        if s.gate:
            step["gate"] = s.gate
        if s.depends_on:
            step["depends_on"] = s.depends_on
        if s.validate_as:
            step["validate_as"] = s.validate_as
        steps.append(step)
    data: dict[str, Any] = {
        "task": body.task,
        "description": body.description,
        "engine": body.engine,
        "input": body.input_text,
        "steps": steps,
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


# ── pydantic bodies ─────────────────────────────────────────────────────────

class FileBody(BaseModel):
    content: str


class RenameBody(BaseModel):
    new_name: str
    content: str


class AgentBody(BaseModel):
    name: str
    tier: int = 3
    reports_to: str | None = None
    domain: str = ""
    model_override: str | None = None
    body: str = ""


class StepBody(BaseModel):
    id: str
    agent: str
    tier: int = 3
    action: str = ""
    gate: str = "auto"
    depends_on: list[str] = []
    validate_as: str | None = None


class PlanBody(BaseModel):
    task: str
    description: str = ""
    engine: str | None = None
    input_text: str = ""
    steps: list[StepBody] = []


# ═════════════════════════════════════════════════════════════════════════════
# AGENTS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/agents", response_class=HTMLResponse)
async def agents_list(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    agents = _list_agents()
    return templates.TemplateResponse(
        request=request, name="edit_agents.html",
        context={"agents": agents},
    )


@router.get("/agents/{tier}/{filename}", response_class=HTMLResponse)
async def agent_edit(request: Request, tier: str, filename: str) -> HTMLResponse:
    filename = _safe_name(filename)
    path = _AGENTS_DIR / tier / filename
    if not path.exists():
        raise HTTPException(404, f"Agent not found: {tier}/{filename}")
    content = path.read_text()
    agent = _parse_agent(content)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="edit_agent.html",
        context={
            "agent": agent,
            "filename": filename,
            "tier": tier,
            "agents_list": _list_agents(),
            "models_list": _list_all_models(),
        },
    )


@router.put("/agents/{tier}/{filename}")
async def agent_save(tier: str, filename: str, body: AgentBody) -> dict[str, str]:
    filename = _safe_name(filename)
    path = _AGENTS_DIR / tier / filename
    if not path.exists():
        raise HTTPException(404, f"Agent not found: {tier}/{filename}")
    path.write_text(_build_agent_md(body))
    return {"status": "saved", "file": f"{tier}/{filename}"}


@router.post("/agents/{tier}")
async def agent_create(tier: str, body: AgentBody) -> dict[str, str]:
    name = body.name.replace(" ", "_").lower()
    if not name.endswith(".md"):
        name += ".md"
    name = _safe_name(name)
    tier_dir = _AGENTS_DIR / tier
    if not tier_dir.is_dir():
        raise HTTPException(422, f"Invalid tier directory: {tier}")
    dest = tier_dir / name
    if dest.exists():
        raise HTTPException(409, f"Agent already exists: {tier}/{name}")
    dest.write_text(_build_agent_md(body))
    return {"status": "created", "file": f"{tier}/{name}"}


@router.delete("/agents/{tier}/{filename}")
async def agent_delete(tier: str, filename: str) -> dict[str, str]:
    filename = _safe_name(filename)
    path = _AGENTS_DIR / tier / filename
    if not path.exists():
        raise HTTPException(404, f"Agent not found: {tier}/{filename}")
    path.unlink()
    return {"status": "deleted", "file": f"{tier}/{filename}"}


# ═════════════════════════════════════════════════════════════════════════════
# PLANS
# ═════════════════════════════════════════════════════════════════════════════

def _list_plans() -> list[str]:
    return [f.name for f in sorted(_PLANS_DIR.glob("*.yaml"))]


@router.get("/plans", response_class=HTMLResponse)
async def plans_list(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    plans = _list_plans()
    return templates.TemplateResponse(
        request=request, name="edit_plans.html",
        context={"plans": plans},
    )


@router.get("/plans/{filename}", response_class=HTMLResponse)
async def plan_edit(request: Request, filename: str) -> HTMLResponse:
    filename = _safe_name(filename)
    path = _PLANS_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Plan not found: {filename}")
    content = path.read_text()
    plan = _parse_plan(content)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="edit_plan.html",
        context={
            "plan": plan,
            "filename": filename,
            "agents_list": _list_agents(),
            "gate_options": ["auto", "human_review"],
            "schema_types": _list_schema_types(),
        },
    )


@router.put("/plans/{filename}")
async def plan_save(filename: str, body: PlanBody) -> dict[str, str]:
    filename = _safe_name(filename)
    path = _PLANS_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Plan not found: {filename}")
    content = _build_plan_yaml(body)
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise HTTPException(422, f"Invalid YAML: {exc}")
    path.write_text(content)
    return {"status": "saved", "file": filename}


@router.post("/plans")
async def plan_create(body: PlanBody) -> dict[str, str]:
    name = body.task.replace(" ", "_").lower()
    if not name.endswith(".yaml"):
        name += ".yaml"
    name = _safe_name(name)
    dest = _PLANS_DIR / name
    if dest.exists():
        raise HTTPException(409, f"Plan already exists: {name}")
    content = _build_plan_yaml(body)
    dest.write_text(content)
    return {"status": "created", "file": name}


@router.delete("/plans/{filename}")
async def plan_delete(filename: str) -> dict[str, str]:
    filename = _safe_name(filename)
    path = _PLANS_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Plan not found: {filename}")
    path.unlink()
    return {"status": "deleted", "file": filename}


# ═════════════════════════════════════════════════════════════════════════════
# CONFIG — models.yaml
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/config", response_class=HTMLResponse)
async def config_edit(request: Request) -> HTMLResponse:
    path = _CONFIG_DIR / "models.yaml"
    content = path.read_text() if path.exists() else ""
    config = _parse_config(content)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="edit_config.html",
        context={"config": config, "all_models": _list_all_models()},
    )


@router.put("/config")
async def config_save(body: FileBody) -> dict[str, str]:
    try:
        yaml.safe_load(body.content)
    except yaml.YAMLError as exc:
        raise HTTPException(422, f"Invalid YAML: {exc}")
    (_CONFIG_DIR / "models.yaml").write_text(body.content)
    return {"status": "saved", "file": "models.yaml"}


# ═════════════════════════════════════════════════════════════════════════════
# ENGINE CONFIGS
# ═════════════════════════════════════════════════════════════════════════════

def _list_engines() -> list[str]:
    return [f.name for f in sorted(_ENGINES_DIR.glob("*.yaml"))]


@router.get("/engines", response_class=HTMLResponse)
async def engines_list(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    engines = _list_engines()
    return templates.TemplateResponse(
        request=request, name="edit_engines.html",
        context={"engines": engines},
    )


@router.get("/engines/{filename}", response_class=HTMLResponse)
async def engine_edit(request: Request, filename: str) -> HTMLResponse:
    filename = _safe_name(filename)
    path = _ENGINES_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Engine config not found: {filename}")
    content = path.read_text()
    engine = yaml.safe_load(content) or {}
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="edit_engine.html",
        context={
            "engine": engine,
            "raw_content": content,
            "filename": filename,
        },
    )


@router.put("/engines/{filename}")
async def engine_save(filename: str, body: FileBody) -> dict[str, str]:
    filename = _safe_name(filename)
    path = _ENGINES_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Engine config not found: {filename}")
    try:
        yaml.safe_load(body.content)
    except yaml.YAMLError as exc:
        raise HTTPException(422, f"Invalid YAML: {exc}")
    path.write_text(body.content)
    return {"status": "saved", "file": filename}


@router.post("/engines")
async def engine_create(body: RenameBody) -> dict[str, str]:
    name = _safe_name(body.new_name if body.new_name.endswith(".yaml") else body.new_name + ".yaml")
    dest = _ENGINES_DIR / name
    if dest.exists():
        raise HTTPException(409, f"Engine config already exists: {name}")
    try:
        yaml.safe_load(body.content)
    except yaml.YAMLError as exc:
        raise HTTPException(422, f"Invalid YAML: {exc}")
    dest.write_text(body.content)
    return {"status": "created", "file": name}


@router.delete("/engines/{filename}")
async def engine_delete(filename: str) -> dict[str, str]:
    filename = _safe_name(filename)
    path = _ENGINES_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Engine config not found: {filename}")
    path.unlink()
    return {"status": "deleted", "file": filename}
