"""SQLModel table definitions for run state persistence."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class PlanRun(SQLModel, table=True):
    __tablename__ = "plan_run"  # type: ignore[assignment]

    run_id: str = Field(primary_key=True)
    plan_path: str
    engine: str = ""
    status: str = "running"  # running | complete | failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StepResult(SQLModel, table=True):
    __tablename__ = "step_result"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="plan_run.run_id", index=True)
    step_id: str
    agent_name: str
    output: str
    gate_approved: bool = True
    gate_feedback: Optional[str] = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)
