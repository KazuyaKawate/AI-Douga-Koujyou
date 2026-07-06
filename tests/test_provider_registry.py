from __future__ import annotations

from src.business_engine.manager import BusinessEngineStore
from src.providers.provider_registry import ProviderRegistry


def test_provider_registry_defaults_to_virtual_without_keys(monkeypatch):
    monkeypatch.delenv("AIOS_EXTERNAL_APIS_ENABLED", raising=False)
    monkeypatch.delenv("AIOS_EXTERNAL_API_ENABLED", raising=False)
    monkeypatch.delenv("AIOS_ENABLED_PROVIDERS", raising=False)
    monkeypatch.delenv("AIOS_ACTIVE_PROVIDER", raising=False)
    monkeypatch.delenv("AIOS_PROVIDER_ENABLED_GEMINI_CLI", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    registry = ProviderRegistry()
    status = registry.status()

    assert status["active_provider"] == "virtual"
    assert status["external_apis_enabled"] is False
    assert status["available_providers"] == ["virtual"]
    assert status["provider_health"]["gemini_cli"]["status"] in {"disabled", "missing"}
    assert status["provider_health"]["openai"]["status"] == "disabled"


def test_provider_registry_falls_back_to_virtual_when_external_provider_disabled(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.delenv("AIOS_EXTERNAL_APIS_ENABLED", raising=False)

    registry = ProviderRegistry(enabled_providers=["openai"])
    result = registry.complete("Write a local-first plan", provider_id="openai")

    assert result.ok is True
    assert result.provider == "virtual"
    assert result.external_request is False
    assert registry.status()["last_provider_call"]


def test_provider_registry_test_mode_still_requires_external_enablement(monkeypatch):
    monkeypatch.setenv("AIOS_PROVIDER_TEST_MODE", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.delenv("AIOS_EXTERNAL_APIS_ENABLED", raising=False)

    registry = ProviderRegistry(enabled_providers=["openai"])
    result = registry.complete("Test prompt", provider_id="openai")

    assert result.provider == "virtual"
    assert result.external_request is False


def test_provider_registry_test_mode_can_simulate_enabled_provider(monkeypatch):
    monkeypatch.setenv("AIOS_PROVIDER_TEST_MODE", "true")
    monkeypatch.setenv("AIOS_EXTERNAL_APIS_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")

    registry = ProviderRegistry(enabled_providers=["gemini"])
    result = registry.complete("Test prompt", provider_id="gemini")

    assert result.ok is True
    assert result.provider == "gemini"
    assert result.external_request is False


def test_provider_registry_supports_claude_alias_in_test_mode(monkeypatch):
    monkeypatch.setenv("AIOS_PROVIDER_TEST_MODE", "true")
    monkeypatch.setenv("AIOS_EXTERNAL_API_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")

    registry = ProviderRegistry(enabled_providers=["anthropic"])
    result = registry.complete("Test prompt", provider_id="claude")

    assert result.ok is True
    assert result.provider == "anthropic"
    assert result.external_request is False


def test_get_provider_registry_reads_enabled_providers_from_env(monkeypatch):
    monkeypatch.setenv("AIOS_ENABLED_PROVIDERS", "gemini_cli,claude")
    monkeypatch.setenv("AIOS_DEFAULT_PROVIDER", "claude")
    monkeypatch.delenv("AIOS_EXTERNAL_APIS_ENABLED", raising=False)
    monkeypatch.delenv("AIOS_EXTERNAL_API_ENABLED", raising=False)

    from src.providers.provider_registry import get_provider_registry

    registry = get_provider_registry()
    status = registry.status()

    assert status["router_default"] == "anthropic"
    assert status["active_provider"] == "virtual"
    assert status["external_apis_enabled"] is False


def test_business_engine_exposes_provider_metrics(tmp_path, monkeypatch):
    monkeypatch.delenv("AIOS_EXTERNAL_APIS_ENABLED", raising=False)
    store = BusinessEngineStore(tmp_path / "business_engine.json")

    metrics = store.beta_metrics()

    assert metrics["active_provider"] == "virtual"
    assert metrics["provider_health"] == "available"
    assert metrics["available_providers"] == "virtual"
    assert metrics["estimated_token_usage"] == 0
