"""Plans API routes — dashboard, run start, SSE streaming."""
from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path
from typing import Any, AsyncGenerator

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from src.orchestrator.engine import PlanExecutor
from src.orchestrator.gate import GateHandler
from src.state.db import DB

router = APIRouter(tags=["Runs"])

_PLANS_DIR: Path = Path(__file__).resolve().parents[3] / "plans"
_CONFIG_DIR: Path = Path(__file__).resolve().parents[3] / "config"

# Sentinel value sent through the queue to signal run completion.
_DONE_SENTINEL = "__STREAM_DONE__"

# Active executors keyed by run_id
_active_executors: dict[str, PlanExecutor] = {}
# Output queues keyed by run_id — bridges sync executor thread → async SSE
_output_queues: dict[str, asyncio.Queue[str]] = {}


def _has_active_provider() -> bool:
    """Return True if at least one provider has its env_key set in the environment."""
    config_path = _CONFIG_DIR / "models.yaml"
    if not config_path.exists():
        return False
    try:
        data = yaml.safe_load(config_path.read_text()) or {}
    except Exception:
        return False
    for prov in data.get("providers", {}).values():
        env_key = prov.get("env_key", "")
        if env_key and os.environ.get(env_key):
            return True
    return False


class RunRequest(BaseModel):
    plan: str
    engine: str = ""
    input_text: str = ""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request) -> HTMLResponse:
    db = DB()
    runs = db.list_runs()
    templates = request.app.state.templates
    plan_files = sorted((_PLANS_DIR / "templates").glob("*.yaml"))
    plans = []
    for pf in plan_files:
        try:
            data = yaml.safe_load(pf.read_text()) or {}
            task = data.get("task") or pf.stem
            label = task.replace("_", " ").title()
        except Exception:
            label = pf.stem.replace("_", " ").title()
        plans.append({"file": pf.name, "label": label})

    # Detect if config is missing or incomplete
    config_path = _CONFIG_DIR / "models.yaml"
    setup_needed = False
    setup_reason = ""
    if not config_path.exists():
        setup_needed = True
        setup_reason = "No model configuration file found."
    else:
        try:
            data = yaml.safe_load(config_path.read_text()) or {}
            tiers = data.get("tiers", {})
            if not any(tiers.get(t, {}).get("model") for t in (1, 2, 3)):
                setup_needed = True
                setup_reason = "No tier models configured yet."
        except Exception:
            setup_needed = True
            setup_reason = "Model configuration file is invalid."

    no_active_providers = not setup_needed and not _has_active_provider()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "runs": runs,
            "plans": plans,
            "setup_needed": setup_needed,
            "setup_reason": setup_reason,
            "no_active_providers": no_active_providers,
        },
    )


@router.post(
    "/plans/run",
    summary="Start a plan run",
    response_description="The new run's ID",
)
async def start_run(body: RunRequest) -> dict[str, str]:
    """Validate the plan name, check that at least one LLM provider has an active API key,
    then launch the plan executor in a background thread. Returns `{run_id}` immediately.
    Connect to `GET /runs/{run_id}/stream` to receive live agent output via SSE."""
    # Prevent path traversal — plan name must be a plain filename
    if Path(body.plan).name != body.plan or "/" in body.plan or "\\" in body.plan:
        raise HTTPException(422, "Invalid plan name — must be a plain filename, no paths.")

    plan_path = _PLANS_DIR / "templates" / body.plan
    if not plan_path.exists():
        raise HTTPException(404, f"Plan not found: {body.plan}")

    if not _has_active_provider():
        raise HTTPException(
            422,
            "No API key is set for any provider. "
            "Go to Setup → API Keys to add a key, then try again.",
        )

    loop = asyncio.get_event_loop()
    q: asyncio.Queue[str] = asyncio.Queue()
    gate_handler = GateHandler()
    gate_handler.set_web_mode()

    def output_cb(text: str) -> None:
        asyncio.run_coroutine_threadsafe(q.put(text), loop)

    executor = PlanExecutor(
        plan_path=plan_path,
        engine_override=body.engine or None,
        gate_handler=gate_handler,
        output_callback=output_cb,
    )
    if body.input_text:
        executor.plan.input = body.input_text

    run_id = executor.run_id
    _active_executors[run_id] = executor
    _output_queues[run_id] = q

    def _run_and_cleanup() -> None:
        try:
            executor.run()
        finally:
            asyncio.run_coroutine_threadsafe(q.put(_DONE_SENTINEL), loop)
            # Clean up references after a short delay to let SSE drain
            def _cleanup() -> None:
                import time
                time.sleep(5)
                _active_executors.pop(run_id, None)
                _output_queues.pop(run_id, None)
            threading.Thread(target=_cleanup, daemon=True).start()

    thread = threading.Thread(target=_run_and_cleanup, daemon=True)
    thread.start()

    return {"run_id": run_id}


@router.get(
    "/runs/{run_id}/stream",
    summary="Stream run output (SSE)",
    response_description="Server-Sent Events stream of agent text chunks",
)
async def stream_run(run_id: str, request: Request) -> StreamingResponse:
    """Server-Sent Events stream for a live run. Each event contains a chunk of agent
    output as HTML-safe text. The special `data: __DONE__` event signals completion.
    Keep-alive comments (`: keep-alive`) are sent every 30 s while idle."""
    q = _output_queues.get(run_id)
    if q is None:
        raise HTTPException(404, f"Run '{run_id}' not found or not streaming.")

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            if await request.is_disconnected():
                break
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=30.0)
                if chunk == _DONE_SENTINEL:
                    yield "data: __DONE__\n\n"
                    break
                safe = chunk.replace("\n", "<br>")
                yield f"data: {safe}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/runs/{run_id}", response_class=HTMLResponse, include_in_schema=False)
async def run_detail(run_id: str, request: Request) -> HTMLResponse:
    db = DB()
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    steps = db.get_completed_steps(run_id)
    templates = request.app.state.templates
    executor = _active_executors.get(run_id)
    plan_steps = executor.plan.steps if executor else []
    return templates.TemplateResponse(
        request=request,
        name="plan_run.html",
        context={
            "run": run,
            "steps": steps,
            "plan_steps": plan_steps,
        },
    )
