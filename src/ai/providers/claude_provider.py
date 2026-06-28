from __future__ import annotations
import json
import time
from pathlib import Path

from ..task import AITask
from ..response import AIResponse
from .base import BaseProvider

# モデル別コスト (USD/1K tokens): (input, output)
_COST_TABLE: dict[str, tuple[float, float]] = {
    "claude-3-haiku":    (0.00025, 0.00125),
    "claude-3-5-haiku":  (0.0008,  0.004),
    "claude-haiku-4-5":  (0.0008,  0.004),
    "claude-3-sonnet":   (0.003,   0.015),
    "claude-3-5-sonnet": (0.003,   0.015),
    "claude-sonnet-4-6": (0.003,   0.015),
    "claude-3-opus":     (0.015,   0.075),
    "claude-opus-4-8":   (0.015,   0.075),
    "claude-opus-4":     (0.015,   0.075),
}

_DEFAULT_TIMEOUT = 60  # seconds


class ClaudeProvider(BaseProvider):

    def __init__(self, name: str, config: dict) -> None:
        super().__init__(name, config)
        self._client_cache = None  # 遅延初期化

    # ---- Public API --------------------------------------------------

    def is_available(self) -> bool:
        if not self._config.get("enabled", True):
            return False
        if self._api_key is None:
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    def complete(self, task: AITask) -> AIResponse:
        model    = self._config.get("model", "claude-sonnet-4-6")
        task_key = task.task_type.value
        timeout  = self._resolve_timeout()
        t0       = time.monotonic()

        try:
            import anthropic
        except ImportError:
            return self._build_error(task_key, model, t0, timeout,
                                     "anthropic パッケージが未インストールです: pip install anthropic>=0.40.0")

        try:
            client           = self._get_client(timeout)
            system, messages = self._build_messages(task)

            kwargs: dict = {
                "model":      model,
                "max_tokens": self._config.get("max_tokens", 8192),
                "messages":   messages,
            }
            if system:
                kwargs["system"] = system

            resp = client.messages.create(**kwargs)

            latency_ms   = int((time.monotonic() - t0) * 1000)
            content      = resp.content[0].text if resp.content else ""
            stop_reason  = resp.stop_reason
            actual_model = resp.model
            in_tokens    = resp.usage.input_tokens
            out_tokens   = resp.usage.output_tokens
            cost_usd     = self._calc_cost(actual_model, in_tokens, out_tokens)

            return AIResponse(
                ok=True,
                content=content,
                provider=self.name,
                model=actual_model,
                task_type=task_key,
                duration_ms=latency_ms,
                metadata={
                    "input_tokens":  in_tokens,
                    "output_tokens": out_tokens,
                    "total_tokens":  in_tokens + out_tokens,
                    "cost_usd":      cost_usd,
                    "stop_reason":   stop_reason,
                    "actual_model":  actual_model,
                    "latency_ms":    latency_ms,
                    "timeout_sec":   timeout,
                    "stub":          False,
                },
            )

        except anthropic.AuthenticationError:
            return self._build_error(task_key, model, t0, timeout, "APIキーが無効です")
        except anthropic.RateLimitError:
            return self._build_error(task_key, model, t0, timeout,
                                     "レート制限超過。しばらく待ってから再試行してください")
        except anthropic.NotFoundError:
            return self._build_error(task_key, model, t0, timeout,
                                     f"モデル {model} が見つかりません")
        except anthropic.BadRequestError as exc:
            return self._build_error(task_key, model, t0, timeout,
                                     f"リクエストエラー: {exc}")
        except anthropic.APITimeoutError:
            return self._build_error(task_key, model, t0, timeout,
                                     f"タイムアウト（{timeout}秒）")
        except anthropic.APIConnectionError:
            return self._build_error(task_key, model, t0, timeout,
                                     "Anthropic への接続に失敗しました")
        except anthropic.APIError as exc:
            return self._build_error(task_key, model, t0, timeout,
                                     f"APIエラー: {exc}")
        except Exception as exc:
            return self._build_error(task_key, model, t0, timeout,
                                     f"予期しないエラー: {exc}")

    # ---- Private -----------------------------------------------------

    def _get_client(self, timeout: int):
        import anthropic
        if self._client_cache is None:
            self._client_cache = anthropic.Anthropic(
                api_key=self._api_key,
                timeout=float(timeout),
            )
        return self._client_cache

    def _build_messages(
        self, task: AITask
    ) -> tuple[str | None, list[dict]]:
        """
        Anthropic は system を top-level パラメータで渡す。
        messages には user / assistant のみ許容。
        """
        system   = task.system_prompt or None
        messages = list(task.context or [])
        messages.append({"role": "user", "content": task.prompt})
        return system, messages

    def _calc_cost(
        self,
        model: str,
        in_tokens: int | None,
        out_tokens: int | None,
    ) -> float | None:
        if in_tokens is None or out_tokens is None:
            return None
        # バージョンサフィックス除去: "claude-sonnet-4-6-20250219" → "claude-sonnet-4-6"
        base = next((k for k in _COST_TABLE if model.startswith(k)), None)
        if base is None:
            return None
        in_rate, out_rate = _COST_TABLE[base]
        return round(in_tokens / 1000 * in_rate + out_tokens / 1000 * out_rate, 8)

    def _resolve_timeout(self) -> int:
        # 優先順位 1: workspace_local.json の claude_request_timeout
        local_file = Path("config/workspace_local.json")
        if local_file.exists():
            try:
                data = json.loads(local_file.read_text(encoding="utf-8"))
                v = data.get("claude_request_timeout")
                if isinstance(v, (int, float)) and v > 0:
                    return int(v)
            except Exception:
                pass
        # 優先順位 2: ai_router.json の provider config
        return int(self._config.get("request_timeout", _DEFAULT_TIMEOUT))

    def _build_error(
        self,
        task_key: str,
        model: str,
        t0: float,
        timeout: int,
        message: str,
    ) -> AIResponse:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return AIResponse(
            ok=False,
            content="",
            provider=self.name,
            model=model,
            task_type=task_key,
            duration_ms=latency_ms,
            error=message,
            metadata={
                "latency_ms":  latency_ms,
                "timeout_sec": timeout,
                "stub":        False,
            },
        )
