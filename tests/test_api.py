"""Tests for the FastAPI web UI — routes, security, and error handling."""
from __future__ import annotations

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture()
def client():
    return TestClient(app)


class TestDashboard:
    def test_dashboard_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Game Studio AI" in resp.text


class TestStartRun:
    def test_plan_not_found_returns_404(self, client):
        resp = client.post("/plans/run", json={"plan": "nonexistent_plan.yaml"})
        assert resp.status_code == 404

    def test_path_traversal_blocked(self, client):
        resp = client.post("/plans/run", json={"plan": "../../etc/passwd"})
        assert resp.status_code == 422

    def test_path_traversal_slash(self, client):
        resp = client.post("/plans/run", json={"plan": "subdir/plan.yaml"})
        assert resp.status_code == 422

    def test_path_traversal_backslash(self, client):
        resp = client.post("/plans/run", json={"plan": "..\\..\\etc\\passwd"})
        assert resp.status_code == 422


class TestGates:
    def test_resolve_gate_no_active_run(self, client):
        resp = client.post(
            "/runs/no-such-id/gate",
            json={"approved": True, "feedback": "ok"},
        )
        assert resp.status_code == 404


class TestSprites:
    def test_sprite_gallery_returns_200(self, client):
        resp = client.get("/sprites")
        assert resp.status_code == 200

    def test_approve_not_found(self, client):
        resp = client.post("/sprites/no_such_sprite.png/approve")
        assert resp.status_code == 404

    def test_reject_not_found(self, client):
        resp = client.post("/sprites/no_such_sprite.png/reject")
        assert resp.status_code == 404


class TestEditorAgents:
    def test_agents_list_200(self, client):
        resp = client.get("/edit/agents")
        assert resp.status_code == 200
        assert "Agents" in resp.text

    def test_agent_edit_200(self, client):
        resp = client.get("/edit/agents/tier1/creative_director.md")
        assert resp.status_code == 200
        assert "creative_director" in resp.text

    def test_agent_edit_not_found(self, client):
        resp = client.get("/edit/agents/tier1/no_such_agent.md")
        assert resp.status_code == 404

    def test_agent_save_round_trip(self, client):
        path = Path("agents/tier1/creative_director.md")
        original = path.read_text()
        try:
            resp = client.put(
                "/edit/agents/tier1/creative_director.md",
                json={
                    "name": "creative_director",
                    "tier": 1,
                    "reports_to": None,
                    "domain": "creative vision",
                    "body": "Test body content",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "saved"
        finally:
            path.write_text(original)

    def test_agent_delete_not_found(self, client):
        resp = client.delete("/edit/agents/tier1/no_such_agent.md")
        assert resp.status_code == 404


class TestEditorPlans:
    def test_plans_list_200(self, client):
        resp = client.get("/edit/plans")
        assert resp.status_code == 200
        assert "Plans" in resp.text

    def test_plan_edit_200(self, client):
        resp = client.get("/edit/plans/design_feature.yaml")
        assert resp.status_code == 200

    def test_plan_save_round_trip(self, client):
        path = Path("plans/templates/design_feature.yaml")
        original = path.read_text()
        try:
            resp = client.put(
                "/edit/plans/design_feature.yaml",
                json={
                    "task": "design_feature",
                    "description": "Test description",
                    "engine": None,
                    "input_text": "Test input",
                    "steps": [
                        {
                            "id": "step_1",
                            "agent": "creative_director",
                            "tier": 1,
                            "action": "Do something",
                            "gate": "auto",
                            "depends_on": [],
                            "validate_as": None,
                        }
                    ],
                },
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "saved"
        finally:
            path.write_text(original)


class TestEditorConfig:
    def test_config_edit_200(self, client):
        resp = client.get("/edit/config")
        assert resp.status_code == 200

    def test_config_save_valid_yaml(self, client):
        path = Path("config/models.yaml")
        original = path.read_text()
        try:
            resp = client.put(
                "/edit/config",
                json={"content": "tiers:\n  1:\n    model: test\n"},
            )
            assert resp.status_code == 200
        finally:
            path.write_text(original)

    def test_config_save_invalid_yaml(self, client):
        path = Path("config/models.yaml")
        original = path.read_text()
        try:
            resp = client.put(
                "/edit/config",
                json={"content": "key: [unclosed\n"},
            )
            assert resp.status_code == 422
        finally:
            path.write_text(original)


class TestEditorEngines:
    def test_engines_list_200(self, client):
        resp = client.get("/edit/engines")
        assert resp.status_code == 200

    def test_engine_edit_200(self, client):
        resp = client.get("/edit/engines/godot4.yaml")
        assert resp.status_code == 200

    def test_engine_save_round_trip(self, client):
        path = Path("config/engines/godot4.yaml")
        original = path.read_text()
        try:
            resp = client.put(
                "/edit/engines/godot4.yaml",
                json={"content": original},
            )
            assert resp.status_code == 200
        finally:
            path.write_text(original)
