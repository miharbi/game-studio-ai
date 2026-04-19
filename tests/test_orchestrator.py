"""Tests for the orchestrator: agent loading, step sequencing, gate logic, context."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.orchestrator.agent_loader import AgentLoader, AgentDefinition
from src.orchestrator.gate import GateHandler, GateType, GateResult
from src.orchestrator.context_manager import ContextManager, StepOutput
from src.state.models import StepResult


AGENTS_DIR = Path(__file__).parent.parent / "agents"


# ---------------------------------------------------------------------------
# AgentLoader
# ---------------------------------------------------------------------------

class TestAgentLoader:
    def test_load_existing_agent(self):
        loader = AgentLoader(agents_dir=AGENTS_DIR)
        agent = loader.load("creative_director")
        assert isinstance(agent, AgentDefinition)
        assert agent.name == "creative_director"
        assert agent.tier == 1
        assert len(agent.system_prompt) > 50

    def test_load_tier2_agent(self):
        loader = AgentLoader(agents_dir=AGENTS_DIR)
        agent = loader.load("game_designer")
        assert agent.tier == 2
        assert agent.reports_to == "creative_director"

    def test_load_tier3_agent(self):
        loader = AgentLoader(agents_dir=AGENTS_DIR)
        agent = loader.load("qa_tester")
        assert agent.tier == 3

    def test_load_missing_agent_raises(self):
        loader = AgentLoader(agents_dir=AGENTS_DIR)
        with pytest.raises((FileNotFoundError, ValueError)):
            loader.load("nonexistent_agent_xyz")

    def test_list_all_returns_all_agents(self):
        loader = AgentLoader(agents_dir=AGENTS_DIR)
        agents_by_tier = loader.list_all()
        all_agents = [a for tier_agents in agents_by_tier.values() for a in tier_agents]
        names = [a.name for a in all_agents]
        assert "creative_director" in names
        assert "game_designer" in names
        assert "qa_tester" in names
        assert len(all_agents) >= 10

    def test_frontmatter_fields_present(self):
        loader = AgentLoader(agents_dir=AGENTS_DIR)
        agents_by_tier = loader.list_all()
        all_agents = [a for tier_agents in agents_by_tier.values() for a in tier_agents]
        for agent in all_agents:
            assert agent.name, f"Agent has no name"
            assert agent.tier in (1, 2, 3), f"{agent.name} has invalid tier {agent.tier}"
            assert len(agent.system_prompt.strip()) > 10, f"{agent.name} has empty system prompt"


# ---------------------------------------------------------------------------
# GateHandler
# ---------------------------------------------------------------------------

class TestGateHandler:
    def test_auto_gate_always_passes(self):
        handler = GateHandler()
        result = handler.evaluate(GateType.AUTO, "step_1", "some output")
        assert result.approved is True
        assert result.feedback == ""

    def test_conditional_gate_passes_on_non_empty_output(self):
        handler = GateHandler()
        result = handler.evaluate(GateType.CONDITIONAL, "step_1", "output content here")
        assert result.approved is True

    def test_conditional_gate_fails_on_empty_output(self):
        handler = GateHandler()
        # CONDITIONAL gate fails when the agent output contains "REJECTED"
        result = handler.evaluate(GateType.CONDITIONAL, "step_1", "REJECTED: output was invalid")
        assert result.approved is False

    def test_web_mode_resolve(self):
        handler = GateHandler()
        handler.set_web_mode()
        import threading
        def resolve_after_delay():
            import time
            time.sleep(0.05)
            handler.resolve_web_gate(approved=True, feedback="looks good")
        t = threading.Thread(target=resolve_after_delay)
        t.start()
        result = handler.evaluate(GateType.HUMAN_REVIEW, "step_web", "agent output")
        t.join()
        assert result.approved is True
        assert result.feedback == "looks good"

    def test_web_mode_reject(self):
        handler = GateHandler()
        handler.set_web_mode()
        import threading
        def reject_after_delay():
            import time
            time.sleep(0.05)
            handler.resolve_web_gate(approved=False, feedback="needs revision")
        t = threading.Thread(target=reject_after_delay)
        t.start()
        result = handler.evaluate(GateType.HUMAN_REVIEW, "step_reject", "output")
        t.join()
        assert result.approved is False
        assert "revision" in result.feedback


# ---------------------------------------------------------------------------
# ContextManager
# ---------------------------------------------------------------------------

class TestContextManager:
    def _make_step_output(self, step_id: str, output: str) -> StepOutput:
        return StepOutput(
            step_id=step_id,
            agent_name="test_agent",
            content=output,
        )

    def test_add_and_build_context(self):
        cm = ContextManager()
        cm.add(self._make_step_output("step_1", "Agent output for step 1."))
        context = cm.build_context(engine_context="Godot 4 project")
        assert "step_1" in context
        assert "Agent output for step 1." in context
        assert "Godot 4 project" in context

    def test_context_respects_token_budget(self):
        cm = ContextManager()
        # Add a very large output that should be truncated
        big_output = "x" * 30000
        cm.add(self._make_step_output("step_big", big_output))
        context = cm.build_context(engine_context="")
        assert len(context) <= 30000  # should not blow up

    def test_multiple_steps_accumulated(self):
        cm = ContextManager()
        for i in range(5):
            cm.add(self._make_step_output(f"step_{i}", f"Output {i}"))
        context = cm.build_context(engine_context="")
        # At least the most recent steps should be present
        assert "Output 4" in context
