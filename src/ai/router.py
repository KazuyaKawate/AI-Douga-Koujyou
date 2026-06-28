from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .task import AITask, TaskType
from .response import AIResponse
from .providers.base import BaseProvider

_DEFAULT_CONFIG = Path("config/ai_router.json")


@dataclass
class RouterConfig:
    version: str
    default_provider: str
    task_routing: dict[str, list[str]]
    providers: dict[str, dict]

    @classmethod
    def load(cls, path: Path = _DEFAULT_CONFIG) -> RouterConfig:
        data = json.loads(path.read_text(encoding="utf-8"))
        # task_routing の値を必ずリストへ正規化（文字列でも動く互換性）
        routing: dict[str, list[str]] = {}
        for task_key, val in data.get("task_routing", {}).items():
            routing[task_key] = val if isinstance(val, list) else [val]
        return cls(
            version=data.get("version", "1.0"),
            default_provider=data.get("default_provider", "openai"),
            task_routing=routing,
            providers=data.get("providers", {}),
        )


class ProviderNotFoundError(Exception):
    pass


class AIRouter:
    def __init__(self, config_path: Path = _DEFAULT_CONFIG) -> None:
        self._config = RouterConfig.load(config_path)
        self._providers: dict[str, BaseProvider] = {}
        self._load_providers()

    # ---- Public API --------------------------------------------------

    def route(self, task: AITask) -> AIResponse:
        t0 = time.monotonic()
        task_key = task.task_type.value

        # 優先順位リストを解決（未定義なら default へ）
        priority: list[str] = (
            self._config.task_routing.get(task_key)
            or self._config.task_routing.get(TaskType.DEFAULT.value)
            or [self._config.default_provider]
        )

        for provider_name in priority:
            provider = self._providers.get(provider_name)
            if provider is None:
                continue
            if not provider.is_available():
                continue
            if not provider.supports(task_key):
                continue
            resp = provider.complete(task)
            resp.duration_ms = int((time.monotonic() - t0) * 1000)
            return resp

        duration_ms = int((time.monotonic() - t0) * 1000)
        return AIResponse(
            ok=False,
            content="",
            provider="none",
            model="",
            task_type=task_key,
            duration_ms=duration_ms,
            error=(
                f"利用可能なプロバイダーが見つかりません "
                f"(task={task_key}, priority={priority})"
            ),
        )

    def get_provider(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def health_check(self) -> dict:
        return {
            "router_version":    self._config.version,
            "default_provider":  self._config.default_provider,
            "providers": {
                name: provider.health_check()
                for name, provider in self._providers.items()
            },
        }

    # ---- Private -----------------------------------------------------

    def _load_providers(self) -> None:
        from .providers import PROVIDER_REGISTRY
        for name, cfg in self._config.providers.items():
            cls = PROVIDER_REGISTRY.get(name)
            if cls is not None:
                # enabled=false でも登録（health_check のため）
                self._providers[name] = cls(name, cfg)
