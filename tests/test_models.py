"""Tests for model router: tier resolution, env overrides, context window, providers."""
from __future__ import annotations

import pytest

import src.models.router as router_module
from src.models.router import get_model, get_context_window, list_providers


@pytest.fixture(autouse=True)
def _reset_config_cache():
    """Ensure each test starts with a fresh config cache."""
    router_module._config = None
    yield
    router_module._config = None


class TestGetModel:
    def test_tier1_default(self):
        assert get_model(1) == "github/gpt-4.1"

    def test_tier2_default(self):
        assert get_model(2) == "github/gpt-4.1-mini"

    def test_tier3_default(self):
        assert get_model(3) == "github/gpt-4.1-mini"

    def test_env_override_tier1(self, monkeypatch):
        monkeypatch.setenv("TIER1_MODEL", "deepseek/deepseek-chat")
        assert get_model(1) == "deepseek/deepseek-chat"

    def test_env_override_tier2(self, monkeypatch):
        monkeypatch.setenv("TIER2_MODEL", "moonshot/moonshot-v1-32k")
        assert get_model(2) == "moonshot/moonshot-v1-32k"

    def test_env_override_tier3(self, monkeypatch):
        monkeypatch.setenv("TIER3_MODEL", "dashscope/qwen-turbo")
        assert get_model(3) == "dashscope/qwen-turbo"

    def test_unknown_tier_returns_fallback(self):
        # Tier 99 is not configured — should fallback to openai/gpt-4o-mini
        result = get_model(99)
        assert isinstance(result, str) and len(result) > 0


class TestGetContextWindow:
    def test_known_model_from_catalog(self):
        ctx = get_context_window("moonshot/moonshot-v1-128k")
        assert ctx == 128000

    def test_known_model_deepseek(self):
        ctx = get_context_window("deepseek/deepseek-chat")
        assert ctx == 65536

    def test_known_model_dashscope(self):
        ctx = get_context_window("dashscope/qwen-max")
        assert ctx == 32768

    def test_known_model_zhipuai(self):
        ctx = get_context_window("zhipuai/glm-4-plus")
        assert ctx == 128000

    def test_unknown_model_returns_default(self):
        ctx = get_context_window("totally_unknown/model-xyz")
        # Should return the safe fallback or something from litellm
        assert isinstance(ctx, int) and ctx > 0


class TestListProviders:
    def test_returns_dict(self):
        providers = list_providers()
        assert isinstance(providers, dict)

    def test_contains_chinese_providers(self):
        providers = list_providers()
        assert "moonshot" in providers
        assert "deepseek" in providers
        assert "dashscope" in providers
        assert "zhipuai" in providers

    def test_contains_western_providers(self):
        providers = list_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "google" in providers
        assert "mistral" in providers

    def test_provider_has_models(self):
        providers = list_providers()
        for name, info in providers.items():
            assert "models" in info, f"Provider {name} missing 'models'"
            assert len(info["models"]) > 0, f"Provider {name} has no models"

    def test_provider_has_env_key(self):
        providers = list_providers()
        for name, info in providers.items():
            assert "env_key" in info, f"Provider {name} missing 'env_key'"

    def test_each_model_has_required_fields(self):
        providers = list_providers()
        for name, info in providers.items():
            for m in info["models"]:
                assert "id" in m, f"Model in {name} missing 'id'"
                assert "context_window" in m, f"Model {m.get('id')} missing 'context_window'"
