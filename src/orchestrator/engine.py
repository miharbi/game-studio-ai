"""Plan executor: reads a plan YAML, resolves agents, and runs steps sequentially.

Handles gates, context passing between agents, and SQLite state persistence.
Supports resuming interrupted runs by run_id.
"""
from __future__ import annotations

import concurrent.futures
import threading
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
        self.depends_on: list[str] = raw.get("depends_on") or []
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
        self._cancelled = threading.Event()
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
        """Execute plan steps respecting the dependency graph.

        Independent steps (no shared deps) run concurrently via a thread pool.
        Steps with dependencies wait until all their parents have completed.
        """
        self.db.ensure_run(self.run_id, str(self.plan.path), self.engine or "")
        already_done = {s.step_id for s in self.db.get_completed_steps(self.run_id)}

        self._emit(f"\n🎬  Plan: {self.plan.task}  [run_id={self.run_id}]\n")

        # Build DAG: in-degree counts and reverse-adjacency list.
        step_map = {s.id: s for s in self.plan.steps}
        in_degree: dict[str, int] = {}
        dependents: dict[str, list[str]] = {s.id: [] for s in self.plan.steps}
        for step in self.plan.steps:
            pending_deps = [d for d in step.depends_on if d in step_map and d not in already_done]
            in_degree[step.id] = len(pending_deps)
            for dep in pending_deps:
                dependents[dep].append(step.id)

        halt = threading.Event()  # set on gate rejection; checked each step
        dep_lock = threading.Lock()  # guards in_degree mutations across threads

        initial_ready = [
            s for s in self.plan.steps
            if in_degree[s.id] == 0 and s.id not in already_done
        ]

        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending: dict[concurrent.futures.Future[None], PlanStep] = {
                pool.submit(self._execute_step, step, halt): step
                for step in initial_ready
            }

            while pending:
                done, _ = concurrent.futures.wait(
                    list(pending.keys()),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for fut in done:
                    step = pending.pop(fut)
                    exc = fut.exception()
                    if exc or halt.is_set():
                        halt.set()
                        continue
                    # Unlock dependents whose in-degree just hit zero.
                    with dep_lock:
                        for child_id in dependents.get(step.id, []):
                            in_degree[child_id] -= 1
                            if in_degree[child_id] == 0:
                                child = step_map[child_id]
                                f = pool.submit(self._execute_step, child, halt)
                                pending[f] = child

        if self._cancelled.is_set():
            self._emit("\n🚫  Run cancelled.")
            self.db.mark_run_failed(self.run_id)
        elif halt.is_set():
            pass  # mark_run_failed already called inside _execute_step
        else:
            self.db.mark_run_complete(self.run_id)
            self._emit(f"\n✅  Plan complete. Output in output/pending/")

    def _execute_step(self, step: PlanStep, halt: threading.Event) -> None:
        """Execute a single step in its own thread. Sets halt on gate rejection."""
        if halt.is_set() or self._cancelled.is_set():
            return

        agent_def = self.loader.load(step.agent)
        self._emit(f"\n▶  Step: {step.id}  agent={step.agent}  tier={agent_def.tier}")

        if self.dry_run:
            self._emit(f"  [dry-run] Would call: {agent_def.name} via {get_model(agent_def.tier, self.engine)}")
            return

        output = self._run_step(step, agent_def)

        if halt.is_set() or self._cancelled.is_set():
            return

        if step.validate_as:
            errors = validate_output(output, step.validate_as)
            if errors:
                self._emit(f"  ⚠  Validation warnings: {errors}")

        # Signal web UI that a gate checkpoint is pending before blocking.
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
            halt.set()

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
