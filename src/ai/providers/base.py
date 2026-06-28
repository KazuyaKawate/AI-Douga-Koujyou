from __future__ import annotations
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path


class BaseProvider(ABC):
    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self._config = config
        self._api_key: str | None = self._resolve_api_key(config)

    # ---- 抽象メソッド ------------------------------------------------

    @abstractmethod
    def complete(self, task: "AITask") -> "AIResponse":  # noqa: F821
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    # ---- Capability --------------------------------------------------

    def get_capabilities(self) -> list[str]:
        return list(self._config.get("capabilities", []))

    def supports(self, task_type: str) -> bool:
        return task_type in self.get_capabilities()

    # ---- Health Check ------------------------------------------------

    def health_check(self) -> dict:
        return {
            "name":               self.name,
            "available":          self.is_available(),
            "api_key_configured": self._api_key is not None,
            "capabilities":       self.get_capabilities(),
            "model":              self._config.get("model", ""),
            "enabled":            self._config.get("enabled", True),
        }

    # ---- 補助 --------------------------------------------------------

    def get_info(self) -> dict:
        return {
            "name":         self.name,
            "model":        self._config.get("model", ""),
            "enabled":      self._config.get("enabled", True),
            "capabilities": self.get_capabilities(),
        }

    def _resolve_api_key(self, config: dict) -> str | None:
        # 優先順位 1: 環境変数
        env_var = config.get("api_key_env", "")
        if env_var:
            key = os.environ.get(env_var, "")
            if key:
                return key

        # 優先順位 2: config/workspace_local.json の ai_keys セクション
        local_path_expr = config.get("api_key_local_path", "")
        if local_path_expr:
            local_file = Path("config/workspace_local.json")
            if local_file.exists():
                try:
                    data = json.loads(local_file.read_text(encoding="utf-8"))
                    val: object = data
                    for key_part in local_path_expr.split("."):
                        if not isinstance(val, dict):
                            break
                        val = val.get(key_part)  # type: ignore[assignment]
                    if isinstance(val, str) and val:
                        return val
                except Exception:
                    pass

        return None
