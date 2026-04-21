"""Database access layer using SQLModel + SQLite."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlmodel import Session, SQLModel, create_engine, select

from src.state.models import PlanRun, StepResult

_DB_PATH: Path = Path(__file__).resolve().parents[2] / "runs.db"
_engine = create_engine(f"sqlite:///{_DB_PATH}", echo=False)


def _ensure_tables() -> None:
    SQLModel.metadata.create_all(_engine)


class DB:
    """Thin data access object around SQLite session state."""

    def __init__(self) -> None:
        _ensure_tables()

    def ensure_run(self, run_id: str, plan_path: str, engine: str) -> PlanRun:
        with Session(_engine) as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                run = PlanRun(run_id=run_id, plan_path=plan_path, engine=engine)
                session.add(run)
                session.commit()
                session.refresh(run)
            return run

    def get_run(self, run_id: str) -> Optional[PlanRun]:
        with Session(_engine) as session:
            return session.get(PlanRun, run_id)

    def get_completed_steps(self, run_id: str) -> list[StepResult]:
        with Session(_engine) as session:
            stmt = select(StepResult).where(StepResult.run_id == run_id)
            return list(session.exec(stmt).all())

    def save_step(
        self,
        run_id: str,
        step_id: str,
        agent_name: str,
        output: str,
        gate_approved: bool,
        gate_feedback: str,
    ) -> None:
        with Session(_engine) as session:
            result = StepResult(
                run_id=run_id,
                step_id=step_id,
                agent_name=agent_name,
                output=output,
                gate_approved=gate_approved,
                gate_feedback=gate_feedback or None,
            )
            session.add(result)
            run = session.get(PlanRun, run_id)
            if run:
                run.updated_at = datetime.now(timezone.utc)
                session.add(run)
            session.commit()

    def mark_run_complete(self, run_id: str) -> None:
        self._update_run_status(run_id, "complete")

    def mark_run_failed(self, run_id: str) -> None:
        self._update_run_status(run_id, "failed")

    def _update_run_status(self, run_id: str, status: str) -> None:
        with Session(_engine) as session:
            run = session.get(PlanRun, run_id)
            if run:
                run.status = status
                run.updated_at = datetime.now(timezone.utc)
                session.add(run)
                session.commit()

    def list_runs(self, limit: int = 20) -> list[PlanRun]:
        with Session(_engine) as session:
            stmt = (
                select(PlanRun)
                .order_by(PlanRun.created_at.desc())  # type: ignore[arg-type]
                .limit(limit)
            )
            return list(session.exec(stmt).all())
