from __future__ import annotations
from ..task import AITask
from ..response import AIResponse
from .base import BaseProvider


class OpenAIProvider(BaseProvider):

    def is_available(self) -> bool:
        return bool(self._config.get("enabled", True))

    def complete(self, task: AITask) -> AIResponse:
        model = self._config.get("model", "gpt-4o")
        task_key = task.task_type.value
        return AIResponse(
            ok=True,
            content=(
                f"[stub:openai/{model}] "
                f"task={task_key} prompt_chars={len(task.prompt)}"
            ),
            provider=self.name,
            model=model,
            task_type=task_key,
            duration_ms=0,
            metadata={"stub": True},
        )
