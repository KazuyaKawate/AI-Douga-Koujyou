"""GeminiProvider — Google Gemini API provider for AIOS Router.

Uses google-genai (新パッケージ). google.generativeai は非推奨のため使用しない。
"""
from __future__ import annotations
import time

from ..task import AITask
from ..response import AIResponse
from .base import BaseProvider


class GeminiProvider(BaseProvider):
    """Google Gemini API プロバイダー。

    google-genai パッケージが必要: pip install google-genai
    config で enabled=true かつ GOOGLE_API_KEY が設定されている場合に利用可能。
    """

    def is_available(self) -> bool:
        if not self._config.get("enabled", False):
            return False
        if not self._api_key:
            return False
        try:
            from google import genai  # noqa: F401
            return True
        except ImportError:
            return False

    def complete(self, task: AITask) -> AIResponse:
        model    = self._config.get("model", "gemini-1.5-flash")
        task_key = task.task_type.value
        t0       = time.monotonic()

        try:
            from google import genai
        except ImportError:
            return self._err(task_key, model, t0, "google-genai 未インストール: pip install google-genai")

        try:
            client  = genai.Client(api_key=self._api_key)
            prompt  = self._build_prompt(task)
            result  = client.models.generate_content(model=model, contents=prompt)
            content = result.text or ""
            latency = int((time.monotonic() - t0) * 1000)

            return AIResponse(
                ok=True,
                content=content,
                provider=self.name,
                model=model,
                task_type=task_key,
                duration_ms=latency,
                metadata={"stub": False, "latency_ms": latency},
            )
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "quota" in msg.lower():
                msg = f"クォータ超過 (Free Tier 上限): {msg[:200]}"
            return self._err(task_key, model, t0, msg)

    # ---- helpers --------------------------------------------------------

    def _build_prompt(self, task: AITask) -> str:
        parts = []
        if task.system_prompt:
            parts.append(task.system_prompt)
        for msg in (task.context or []):
            role    = msg.get("role", "")
            content = msg.get("content", "")
            parts.append(f"[{role}] {content}")
        parts.append(task.prompt)
        return "\n\n".join(parts)

    def _err(self, task_key: str, model: str, t0: float, msg: str) -> AIResponse:
        return AIResponse(
            ok=False, content="", provider=self.name, model=model,
            task_type=task_key, duration_ms=int((time.monotonic() - t0) * 1000),
            error=msg, metadata={"stub": False},
        )
