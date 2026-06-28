from __future__ import annotations
from ..task import AITask
from ..response import AIResponse
from .base import BaseProvider


class ClaudeProvider(BaseProvider):

    def is_available(self) -> bool:
        return bool(self._config.get("enabled", True))

    def complete(self, task: AITask) -> AIResponse:
        model = self._config.get("model", "claude-sonnet-4-6")
        task_key = task.task_type.value
        return AIResponse(
            ok=True,
            content=(
                f"[stub:claude/{model}] "
                f"task={task_key} prompt_chars={len(task.prompt)}"
            ),
            provider=self.name,
            model=model,
            task_type=task_key,
            duration_ms=0,
            metadata={"stub": True},
        )
