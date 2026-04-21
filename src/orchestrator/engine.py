"""Plan executor: reads a plan YAML, resolves agents, and runs steps sequentially.

Handles gates, context passing between agents, and SQLite state persistence.
Supports resuming interrupted runs by run_id.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable

import yaml

from src.models.client import LLMClient
from src.models.router import get_model
from src.orchestrator.agent_loader import AgentLoader, AgentDefinition
from src.orchestrator.context_manager import ContextManager, StepOutput
from src.orchestrator.gate import GateHandler, GateType, GateResult
from src.engines.detect import load_engine_context
from src.state.db import DB
from src.validators.schema import validate_output

_AGENTS_DIR: Path = Path(__file__).resolve().parents[2] / "agents"


class PlanStep:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.id: str = raw.get("id", raw["agent"])
        self.agent: str = raw["agent"]
        self.action: str = raw["action"]
        self.depends_on: str | None = raw.get("depends_on")
        self.gate: GateType = GateType(raw.get("gate", "auto"))
        self.validate_as: str | None = raw.get("validate_as")


class Plan:
    def __init__(self, path: Path) -> None:
        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f)
        self.task: str = data["task"]
        self.description: str = data.get("description", "")
        self.engine: str | None = data.get("engine")
        self.input: str = data.get("input", "")
        self.steps: list[PlanStep] = [PlanStep(s) for s in data["steps"]]
        self.path = path


class PlanExecutor:
    """Executes a plan YAML file through the agent pipeline."""

    def __init__(
        self,
        plan_path: Path,
        engine_override: str | None = None,
        dry_run: bool = False,
        run_id: str | None = None,
        gate_handler: GateHandler | None = None,
        output_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.plan = Plan(plan_path)
        self.engine = engine_override or self.plan.engine
        self.dry_run = dry_run
        self.run_id: str = run_id or str(uuid.uuid4())[:8]
        self.loader = AgentLoader(_AGENTS_DIR)
        self.context = ContextManager()
        self.gate_handler = gate_handler or GateHandler()
        self.db = DB()
        self.output_callback = output_callback
        self._engine_context: str = (
            load_engine_context(self.engine) if self.engine else ""
        )

    @classmethod
    def from_run_id(cls, run_id: str) -> "PlanExecutor":
        """Reconstruct an executor from a saved run, ready to resume."""
        db = DB()
        plan_run = db.get_run(run_id)
        if not plan_run:
            raise ValueError(f"Run '{run_id}' not found in database.")
        executor = cls(
            plan_path=Path(plan_run.plan_path),
            engine_override=plan_run.engine or None,
            run_id=run_id,
        )
        for step_result in db.get_completed_steps(run_id):
            executor.context.add(
                StepOutput(
                    step_id=step_result.step_id,
                    agent_name=step_result.agent_name,
                    content=step_result.output,
                    gate_feedback=step_result.gate_feedback or "",
                )
            )
        return executor

    def run(self) -> None:
        """Execute all plan steps in order, respecting gates and saved state."""
        self.db.ensure_run(self.run_id, str(self.plan.path), self.engine or "")
        completed_ids = {
            s.step_id for s in self.db.get_completed_steps(self.run_id)
        }

        self._emit(f"\n🎬  Plan: {self.plan.task}  [run_id={self.run_id}]\n")

        for step in self.plan.steps:
            if step.id in completed_ids:
                self._emit(f"  ↩  Skipping (already completed): {step.id}")
                continue

            agent_def = self.loader.load(step.agent)
            self._emit(
                f"\n▶  Step: {step.id}  agent={step.agent}  tier={agent_def.tier}"
            )

            if self.dry_run:
                self._emit(f"  [dry-run] Would call: {agent_def.name} via {get_model(agent_def.tier, self.engine)}")
                continue

            output = self._run_step(step, agent_def)

            if step.validate_as:
                errors = validate_output(output, step.validate_as)
                if errors:
                    self._emit(f"  ⚠  Validation warnings: {errors}")

            # Signal web UI that a gate is pending before blocking
            if step.gate == GateType.HUMAN_REVIEW:
                self._emit(f"__GATE__:{step.id}")

            gate_result = self.gate_handler.evaluate(
                gate_type=step.gate,
                step_id=step.id,
                agent_output=output,
                run_id=self.run_id,
            )

            self.db.save_step(
                run_id=self.run_id,
                step_id=step.id,
                agent_name=step.agent,
                output=output,
                gate_approved=gate_result.approved,
                gate_feedback=gate_result.feedback,
            )

            self.context.add(
                StepOutput(
                    step_id=step.id,
                    agent_name=step.agent,
                    content=output,
                    gate_feedback=gate_result.feedback,
                )
            )

            if not gate_result.approved:
                self._emit(f"\n✋  Step '{step.id}' rejected. Plan halted.")
                self.db.mark_run_failed(self.run_id)
                return

        self.db.mark_run_complete(self.run_id)
        self._emit(f"\n✅  Plan complete. Output in output/pending/")

    def _run_step(self, step: PlanStep, agent: AgentDefinition) -> str:
        """Call the LLM for a single step and return the full output."""
        model = agent.model_override or get_model(agent.tier, self.engine)
        client = LLMClient(model)

        context_block = self.context.build_context(self._engine_context, model=model)
        system = agent.system_prompt
        if context_block:
            system = f"{system}\n\n---\n\n{context_block}"

        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Task: {self.plan.task}\n\n"
                    f"Your action: {step.action}\n\n"
                    f"Input: {self.plan.input}"
                ),
            },
        ]

        full_output: list[str] = []
        for chunk in client.stream(messages):
            full_output.append(chunk)
            self._emit(chunk, end="")

        self._emit("")  # newline after streaming
        return "".join(full_output)

    def _emit(self, text: str, end: str = "\n") -> None:
        """Emit output to stdout and/or the web UI output callback."""
        print(text, end=end, flush=True)
        if self.output_callback:
            self.output_callback(text + end)
