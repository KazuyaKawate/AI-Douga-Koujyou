from __future__ import annotations
import json
import time
from pathlib import Path

from ..task import AITask
from ..response import AIResponse
from .base import BaseProvider

# モデル別コスト (USD/1K tokens): (input, output)
_COST_TABLE: dict[str, tuple[float, float]] = {
    "gpt-4o":        (0.0025,  0.010),
    "gpt-4o-mini":   (0.00015, 0.0006),
    "gpt-4-turbo":   (0.010,   0.030),
    "gpt-3.5-turbo": (0.0005,  0.0015),
}

_DEFAULT_TIMEOUT = 60  # seconds


class OpenAIProvider(BaseProvider):

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
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def complete(self, task: AITask) -> AIResponse:
        model    = self._config.get("model", "gpt-4o")
        task_key = task.task_type.value
        timeout  = self._resolve_timeout()
        t0       = time.monotonic()

        try:
            import openai
        except ImportError:
            return self._build_error(task_key, model, t0, timeout,
                                     "openai パッケージが未インストールです: pip install openai>=1.0.0")

        try:
            client   = self._get_client()
            messages = self._build_messages(task)

            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=self._config.get("max_tokens", 4096),
                temperature=self._config.get("temperature", 0.7),
                timeout=float(timeout),
            )

            latency_ms    = int((time.monotonic() - t0) * 1000)
            content       = resp.choices[0].message.content or ""
            finish_reason = resp.choices[0].finish_reason
            actual_model  = resp.model
            usage         = resp.usage
            in_tokens     = usage.prompt_tokens     if usage else None
            out_tokens    = usage.completion_tokens if usage else None
            total_tokens  = usage.total_tokens      if usage else None
            cost_usd      = self._calc_cost(actual_model, in_tokens, out_tokens)

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
                    "total_tokens":  total_tokens,
                    "cost_usd":      cost_usd,
                    "finish_reason": finish_reason,
                    "actual_model":  actual_model,
                    "latency_ms":    latency_ms,
                    "timeout_sec":   timeout,
                    "stub":          False,
                },
            )

        except openai.AuthenticationError:
            return self._build_error(task_key, model, t0, timeout, "APIキーが無効です")
        except openai.RateLimitError:
            return self._build_error(task_key, model, t0, timeout,
                                     "レート制限超過。しばらく待ってから再試行してください")
        except openai.NotFoundError:
            return self._build_error(task_key, model, t0, timeout,
                                     f"モデル {model} が見つかりません")
        except openai.BadRequestError as exc:
            return self._build_error(task_key, model, t0, timeout,
                                     f"リクエストエラー: {exc}")
        except openai.APITimeoutError:
            return self._build_error(task_key, model, t0, timeout,
                                     f"タイムアウト（{timeout}秒）")
        except openai.APIConnectionError:
            return self._build_error(task_key, model, t0, timeout,
                                     "OpenAI への接続に失敗しました")
        except openai.APIError as exc:
            return self._build_error(task_key, model, t0, timeout,
                                     f"APIエラー: {exc}")
        except Exception as exc:
            return self._build_error(task_key, model, t0, timeout,
                                     f"予期しないエラー: {exc}")

    # ---- Private -----------------------------------------------------

    def _get_client(self):
        import openai
        if self._client_cache is None:
            self._client_cache = openai.OpenAI(api_key=self._api_key)
        return self._client_cache

    def _build_messages(self, task: AITask) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if task.system_prompt:
            messages.append({"role": "system", "content": task.system_prompt})
        for ctx in (task.context or []):
            messages.append(ctx)
        messages.append({"role": "user", "content": task.prompt})
        return messages

    def _calc_cost(
        self,
        model: str,
        in_tokens: int | None,
        out_tokens: int | None,
    ) -> float | None:
        if in_tokens is None or out_tokens is None:
            return None
        # バージョンサフィックス除去: "gpt-4o-2024-11-20" → "gpt-4o"
        base = next((k for k in _COST_TABLE if model.startswith(k)), None)
        if base is None:
            return None
        in_rate, out_rate = _COST_TABLE[base]
        return round(in_tokens / 1000 * in_rate + out_tokens / 1000 * out_rate, 8)

    def _resolve_timeout(self) -> int:
        # 優先順位 1: workspace_local.json の openai_request_timeout
        local_file = Path("config/workspace_local.json")
        if local_file.exists():
            try:
                data = json.loads(local_file.read_text(encoding="utf-8"))
                v = data.get("openai_request_timeout")
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
