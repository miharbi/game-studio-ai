"""Gate decision API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.routes.plans import _active_executors

router = APIRouter()


class GateDecision(BaseModel):
    approved: bool
    feedback: str = ""


@router.post("/runs/{run_id}/gate")
async def resolve_gate(run_id: str, body: GateDecision) -> dict[str, str]:
    executor = _active_executors.get(run_id)
    if not executor:
        raise HTTPException(404, f"No active run: '{run_id}'")
    executor.gate_handler.resolve_web_gate(body.approved, body.feedback)
    status = "approved" if body.approved else "rejected"
    return {"status": status, "run_id": run_id}
