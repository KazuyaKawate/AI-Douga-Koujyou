from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def external_apis_enabled() -> bool:
    plural = os.getenv("AIOS_EXTERNAL_APIS_ENABLED")
    singular = os.getenv("AIOS_EXTERNAL_API_ENABLED")
    value = plural if plural is not None else singular
    return str(value or "false").strip().lower() in {"1", "true", "yes", "on"}


def test_mode_enabled() -> bool:
    return os.getenv("AIOS_PROVIDER_TEST_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class ProviderResult:
    ok: bool
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    external_request: bool = False
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseProvider:
    provider_id = "base"
    name = "Base Provider"
    env_key = ""
    model = ""
    external = True

    def __init__(self, *, enabled: bool = False, test_mode: bool | None = None) -> None:
        self.enabled = bool(enabled)
        self.test_mode = test_mode_enabled() if test_mode is None else bool(test_mode)
        self.last_call_at = ""
        self.estimated_token_usage = 0

    def has_key(self) -> bool:
        return bool(self.env_key and os.getenv(self.env_key))

    def is_available(self) -> bool:
        if not self.external:
            return True
        return self.enabled and external_apis_enabled() and self.has_key()

    def health(self) -> dict[str, Any]:
        if not self.external:
            status = "available"
        elif not external_apis_enabled():
            status = "disabled"
        elif not self.enabled:
            status = "disabled"
        elif not self.has_key():
            status = "missing_key"
        else:
            status = "available"
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "enabled": self.enabled,
            "available": self.is_available(),
            "status": status,
            "env_key": self.env_key,
            "model": self.model,
            "last_call_at": self.last_call_at,
            "estimated_token_usage": self.estimated_token_usage,
            "external": self.external,
        }

    def complete(self, prompt: str, **_: Any) -> ProviderResult:
        if not self.is_available():
            return ProviderResult(
                ok=False,
                content="",
                provider=self.provider_id,
                model=self.model,
                error="Provider is disabled or missing credentials.",
            )
        if self.test_mode:
            return self._test_response(prompt)
        return ProviderResult(
            ok=False,
            content="",
            provider=self.provider_id,
            model=self.model,
            error="External provider calls are not implemented in local-first mode.",
        )

    def _test_response(self, prompt: str) -> ProviderResult:
        self.last_call_at = datetime.now().isoformat(timespec="seconds")
        input_tokens = estimate_tokens(prompt)
        output_tokens = 24
        self.estimated_token_usage += input_tokens + output_tokens
        return ProviderResult(
            ok=True,
            content=f"[{self.name} test mode] {prompt[:120]}",
            provider=self.provider_id,
            model=self.model or "test-model",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            external_request=False,
            metadata={"test_mode": True},
        )


class VirtualProvider(BaseProvider):
    provider_id = "virtual"
    name = "Virtual Provider"
    env_key = ""
    model = "virtual-local"
    external = False

    def __init__(self, *, enabled: bool = True, test_mode: bool | None = None) -> None:
        super().__init__(enabled=enabled, test_mode=test_mode)

    def complete(self, prompt: str, **_: Any) -> ProviderResult:
        self.last_call_at = datetime.now().isoformat(timespec="seconds")
        input_tokens = estimate_tokens(prompt)
        output_tokens = 32
        self.estimated_token_usage += input_tokens + output_tokens
        return ProviderResult(
            ok=True,
            content=f"[Virtual Provider] {prompt[:160]}",
            provider=self.provider_id,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            external_request=False,
            metadata={"local_first": True},
        )


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text or "") / 4))
