"""Plans API routes — dashboard, run start, SSE streaming."""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from src.orchestrator.engine import PlanExecutor
from src.orchestrator.gate import GateHandler
from src.state.db import DB

router = APIRouter()

_PLANS_DIR: Path = Path(__file__).resolve().parents[3] / "plans"

# Sentinel value sent through the queue to signal run completion.
_DONE_SENTINEL = "__STREAM_DONE__"

# Active executors keyed by run_id
_active_executors: dict[str, PlanExecutor] = {}
# Output queues keyed by run_id — bridges sync executor thread → async SSE
_output_queues: dict[str, asyncio.Queue[str]] = {}


class RunRequest(BaseModel):
    plan: str
    engine: str = ""
    input_text: str = ""


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    db = DB()
    runs = db.list_runs()
    templates = request.app.state.templates
    plans = sorted((_PLANS_DIR / "templates").glob("*.yaml"))
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"runs": runs, "plans": [p.name for p in plans]},
    )


@router.post("/plans/run")
async def start_run(body: RunRequest) -> dict[str, str]:
    # Prevent path traversal — plan name must be a plain filename
    if Path(body.plan).name != body.plan or "/" in body.plan or "\\" in body.plan:
        raise HTTPException(422, "Invalid plan name — must be a plain filename, no paths.")

    plan_path = _PLANS_DIR / "templates" / body.plan
    if not plan_path.exists():
        raise HTTPException(404, f"Plan not found: {body.plan}")

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


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str, request: Request) -> StreamingResponse:
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


@router.get("/runs/{run_id}", response_class=HTMLResponse)
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
