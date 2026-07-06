from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from src.providers.anthropic_provider import AnthropicProvider
from src.providers.base_provider import BaseProvider, ProviderResult, VirtualProvider, external_apis_enabled
from src.providers.gemini_cli_provider import GeminiCLIProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.openai_provider import OpenAIProvider


PROVIDER_CLASSES: dict[str, type[BaseProvider]] = {
    "virtual": VirtualProvider,
    "gemini_cli": GeminiCLIProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}

PROVIDER_ALIASES = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "gemini-cli": "gemini_cli",
    "gemini_cli": "gemini_cli",
    "virtual": "virtual",
    "gemini": "gemini",
    "openai": "openai",
}


class ProviderRegistry:
    """Local-first AI provider registry.

    External provider adapters are discoverable, but they never make API calls
    unless global external APIs are explicitly enabled and credentials exist.
    """

    def __init__(
        self,
        *,
        default_provider: str = "virtual",
        enabled_providers: list[str] | None = None,
        test_mode: bool | None = None,
    ) -> None:
        self.default_provider = default_provider or "virtual"
        self.enabled_providers = set(enabled_providers or [])
        self.test_mode = test_mode
        self.providers: dict[str, BaseProvider] = {}
        self.last_provider_call = ""
        self.last_provider_id = ""
        self.last_generation_time_ms = 0
        self.provider_errors = 0
        self.last_error = ""
        self.estimated_token_usage = 0
        self.register_defaults()

    def register(self, provider_id: str, provider: BaseProvider) -> None:
        self.providers[provider_id] = provider

    def register_defaults(self) -> None:
        for provider_id, provider_cls in PROVIDER_CLASSES.items():
            enabled = provider_id == "virtual" or provider_id in self.enabled_providers
            self.register(provider_id, provider_cls(enabled=enabled, test_mode=self.test_mode))

    def select_active_provider(self, requested: str | None = None) -> BaseProvider:
        candidates = [requested, os.getenv("AIOS_ACTIVE_PROVIDER"), self.default_provider, "virtual"]
        for provider_id in candidates:
            if not provider_id:
                continue
            provider = self.providers.get(_normalize_provider_id(provider_id))
            if provider and provider.is_available():
                return provider
        return self.providers["virtual"]

    def complete(self, prompt: str, provider_id: str | None = None, **kwargs: Any) -> ProviderResult:
        started = datetime.now()
        provider = self.select_active_provider(provider_id)
        result = provider.complete(prompt, **kwargs)
        if not result.ok and provider.provider_id != "virtual":
            self.provider_errors += 1
            self.last_error = result.error
            provider = self.providers["virtual"]
            result = provider.complete(prompt, **kwargs)
        self.last_provider_call = datetime.now().isoformat(timespec="seconds")
        self.last_provider_id = result.provider
        self.last_generation_time_ms = int((datetime.now() - started).total_seconds() * 1000)
        if not result.ok:
            self.provider_errors += 1
            self.last_error = result.error
        self.estimated_token_usage += result.input_tokens + result.output_tokens
        return result

    def status(self) -> dict[str, Any]:
        active = self.select_active_provider()
        provider_health = {
            provider_id: provider.health()
            for provider_id, provider in self.providers.items()
        }
        available = [
            provider_id
            for provider_id, health in provider_health.items()
            if health["available"]
        ]
        return {
            "router_default": self.default_provider,
            "external_apis_enabled": external_apis_enabled(),
            "active_provider": active.provider_id,
            "provider_health": provider_health,
            "available_providers": available,
            "last_provider_call": self.last_provider_call,
            "last_provider_id": self.last_provider_id,
            "last_generation_time_ms": self.last_generation_time_ms,
            "estimated_token_usage": self.estimated_token_usage,
            "provider_errors": self.provider_errors,
            "last_error": self.last_error,
        }


def get_provider_registry() -> ProviderRegistry:
    return ProviderRegistry(
        default_provider=_normalize_provider_id(os.getenv("AIOS_DEFAULT_PROVIDER", "virtual")),
        enabled_providers=_enabled_providers_from_env(),
    )


def _normalize_provider_id(provider_id: str) -> str:
    return PROVIDER_ALIASES.get(str(provider_id or "virtual").strip().lower(), "virtual")


def _enabled_providers_from_env() -> list[str]:
    enabled: set[str] = set()
    raw = os.getenv("AIOS_ENABLED_PROVIDERS", "")
    for provider_id in raw.split(","):
        normalized = _normalize_provider_id(provider_id)
        if normalized != "virtual":
            enabled.add(normalized)
    for provider_id in PROVIDER_CLASSES:
        env_name = f"AIOS_PROVIDER_ENABLED_{provider_id.upper()}"
        if os.getenv(env_name, "false").strip().lower() in {"1", "true", "yes", "on"}:
            enabled.add(provider_id)
    if os.getenv("AIOS_PROVIDER_ENABLED_CLAUDE", "false").strip().lower() in {"1", "true", "yes", "on"}:
        enabled.add("anthropic")
    return sorted(enabled)
