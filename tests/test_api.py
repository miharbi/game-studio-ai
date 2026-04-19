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
