"""Gate decision API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.routes.plans import _active_executors

router = APIRouter(tags=["Runs"])


class GateDecision(BaseModel):
    approved: bool
    feedback: str = ""


@router.post(
    "/runs/{run_id}/gate",
    summary="Resolve a gate checkpoint",
    response_description="Gate resolution status",
)
async def resolve_gate(run_id: str, body: GateDecision) -> dict[str, str]:
    """Approve or reject a `human_review` gate for the specified run.
    Approved gates let the pipeline continue; rejected gates halt the run
    and the agent receives the feedback string."""
    executor = _active_executors.get(run_id)
    if not executor:
        raise HTTPException(404, f"No active run: '{run_id}'")
    executor.gate_handler.resolve_web_gate(body.approved, body.feedback)
    status = "approved" if body.approved else "rejected"
    return {"status": status, "run_id": run_id}
