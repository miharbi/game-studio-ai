"""Manages context window across pipeline steps.

Collects previous step outputs and truncates to stay within the token budget.
Supports dynamic context sizing based on the target model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Conservative estimate: 1 token ≈ 4 chars.
# Leave headroom for system prompt body + new response.
_CHARS_PER_TOKEN: int = 4
_DEFAULT_CONTEXT_TOKENS: int = 6000
_DEFAULT_CONTEXT_CHARS: int = _DEFAULT_CONTEXT_TOKENS * _CHARS_PER_TOKEN


@dataclass
class StepOutput:
    step_id: str
    agent_name: str
    content: str
    gate_feedback: str = ""


@dataclass
class ContextManager:
    """Accumulates step outputs and builds context for the next agent."""

    _outputs: list[StepOutput] = field(default_factory=list)

    def add(self, output: StepOutput) -> None:
        self._outputs.append(output)

    def build_context(self, engine_context: str = "", model: str | None = None) -> str:
        """
        Build a context string for the next agent prompt.
        Truncates oldest outputs first if over budget.

        If *model* is provided, the char budget scales to that model's
        context window (using ~25% of it for prior-step context).
        """
        max_chars = self._max_chars(model)

        parts: list[str] = []
        if engine_context:
            parts.append(f"## Engine Context\n{engine_context}")

        budget: int = max_chars - sum(len(p) for p in parts)
        output_parts: list[str] = []

        for out in reversed(self._outputs):
            block = _format_output(out)
            if len(block) > budget:
                block = block[:budget] + "\n[...truncated]"
                output_parts.insert(0, block)
                break
            budget -= len(block)
            output_parts.insert(0, block)

        parts.extend(output_parts)
        return "\n\n".join(parts)

    def clear(self) -> None:
        self._outputs.clear()

    @staticmethod
    def _max_chars(model: str | None) -> int:
        """Derive max chars from model context window, or use default."""
        if model is None:
            return _DEFAULT_CONTEXT_CHARS
        try:
            from src.models.router import get_context_window
            ctx_tokens = get_context_window(model)
            # Use ~25% of total context for prior-step outputs
            return max(ctx_tokens // 4, _DEFAULT_CONTEXT_TOKENS) * _CHARS_PER_TOKEN
        except Exception:
            return _DEFAULT_CONTEXT_CHARS


def _format_output(out: StepOutput) -> str:
    lines = [f"## Output from: {out.agent_name} (step: {out.step_id})"]
    lines.append(out.content)
    if out.gate_feedback:
        lines.append(f"\n**Human feedback:** {out.gate_feedback}")
    return "\n".join(lines)
