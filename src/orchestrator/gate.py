"""Human gate system.

Gate types:
  - human_review: pauses the pipeline and waits for approval (CLI or web)
  - auto:         always passes through
  - conditional:  agent output must contain APPROVED or REJECTED

In web mode, call set_web_mode() before running. Gates will block until
resolve_web_gate() is called by the HTTP endpoint.
"""
from __future__ import annotations

import queue
from enum import Enum


class GateType(str, Enum):
    HUMAN_REVIEW = "human_review"
    AUTO = "auto"
    CONDITIONAL = "conditional"


class GateResult:
    def __init__(self, approved: bool, feedback: str = "") -> None:
        self.approved = approved
        self.feedback = feedback

    def __bool__(self) -> bool:
        return self.approved


class GateHandler:
    """
    Handles gate decisions.

    CLI mode (default): blocks on stdin input().
    Web mode: blocks on a threading.Queue until resolve_web_gate() is called.
    """

    def __init__(self) -> None:
        self._web_queue: queue.Queue[tuple[bool, str]] | None = None

    def set_web_mode(self) -> None:
        """Enable web mode — gates wait for resolve_web_gate() instead of stdin."""
        self._web_queue = queue.Queue()

    def resolve_web_gate(self, approved: bool, feedback: str = "") -> None:
        """Called by the HTTP gate route to unblock a waiting gate."""
        if self._web_queue is not None:
            self._web_queue.put((approved, feedback))

    def evaluate(
        self,
        gate_type: GateType,
        step_id: str,
        agent_output: str,
        run_id: str = "",
    ) -> GateResult:
        if gate_type == GateType.AUTO:
            return GateResult(approved=True)

        if gate_type == GateType.HUMAN_REVIEW:
            if self._web_queue is not None:
                return self._web_review(step_id)
            return self._cli_review(step_id, agent_output)

        if gate_type == GateType.CONDITIONAL:
            upper = agent_output.upper()
            if "REJECTED" in upper:
                return GateResult(approved=False, feedback="Agent self-rejected.")
            return GateResult(approved=True)

        return GateResult(approved=True)

    def _web_review(self, step_id: str) -> GateResult:
        """Block until the web UI resolves the gate (10 minute timeout)."""
        assert self._web_queue is not None
        try:
            approved, feedback = self._web_queue.get(timeout=600)
            return GateResult(approved=approved, feedback=feedback)
        except queue.Empty:
            return GateResult(approved=False, feedback="Gate timed out after 10 minutes.")

    def _cli_review(self, step_id: str, agent_output: str) -> GateResult:
        print(f"\n{'=' * 60}")
        print(f"GATE: {step_id}")
        print(f"{'=' * 60}")
        print(agent_output[:2000])
        if len(agent_output) > 2000:
            print("[...output truncated for display...]")
        print(f"{'=' * 60}")
        choice = input("Approve? [y / n / feedback text]: ").strip()
        if choice.lower() in ("y", "yes", ""):
            return GateResult(approved=True)
        if choice.lower() in ("n", "no"):
            return GateResult(approved=False)
        # Any other text is treated as rejection feedback
        return GateResult(approved=False, feedback=choice)
