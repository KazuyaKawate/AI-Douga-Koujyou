from __future__ import annotations
import datetime
import json
import time
from dataclasses import dataclass
from pathlib import Path

from .task import AITask, TaskType
from .response import AIResponse
from .logger import BaseRouterLogger, LogEntry, NullLogger
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
    def __init__(
        self,
        config_path: Path = _DEFAULT_CONFIG,
        logger: BaseRouterLogger | None = None,
    ) -> None:
        self._config = RouterConfig.load(config_path)
        self._providers: dict[str, BaseProvider] = {}
        self._logger: BaseRouterLogger = logger if logger is not None else NullLogger()
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

        resp: AIResponse | None = None
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
            break

        if resp is None:
            duration_ms = int((time.monotonic() - t0) * 1000)
            resp = AIResponse(
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

        self._emit_log(resp, task_key)
        return resp

    def get_provider(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def health_check(self) -> dict:
        return {
            "router_version":   self._config.version,
            "default_provider": self._config.default_provider,
            "providers": {
                name: provider.health_check()
                for name, provider in self._providers.items()
            },
        }

    # ---- Private -----------------------------------------------------

    def _emit_log(self, resp: AIResponse, task_key: str) -> None:
        meta = resp.metadata or {}
        entry = LogEntry(
            task_type=task_key,
            provider=resp.provider,
            model=resp.model,
            latency_ms=resp.duration_ms,
            success=resp.ok,
            input_tokens=meta.get("input_tokens"),
            output_tokens=meta.get("output_tokens"),
            cost_usd=meta.get("cost_usd"),
            error_message=resp.error,
        )
        self._logger.log(entry)

    def _load_providers(self) -> None:
        from .providers import PROVIDER_REGISTRY
        for name, cfg in self._config.providers.items():
            cls = PROVIDER_REGISTRY.get(name)
            if cls is not None:
                # enabled=false でも登録（health_check のため）
                self._providers[name] = cls(name, cfg)
