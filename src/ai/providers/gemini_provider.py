from __future__ import annotations
from ..task import AITask
from ..response import AIResponse
from .base import BaseProvider


class GeminiProvider(BaseProvider):
    """Gemini スタブ。config で enabled=false のため通常は routing 対象外。"""

    def is_available(self) -> bool:
        return bool(self._config.get("enabled", False))

    def complete(self, task: AITask) -> AIResponse:
        model = self._config.get("model", "gemini-2.0-flash")
        task_key = task.task_type.value
        return AIResponse(
            ok=True,
            content=(
                f"[stub:gemini/{model}] "
                f"task={task_key} prompt_chars={len(task.prompt)}"
            ),
            provider=self.name,
            model=model,
            task_type=task_key,
            duration_ms=0,
            metadata={"stub": True},
        )
