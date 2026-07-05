from __future__ import annotations
from typing import TYPE_CHECKING, Any

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


class AITaskExecutor(BaseStepExecutor):
    """
    AIRouter.complete() を呼び出すExecutor。

    config フィールド:
        prompt      : str  テンプレート文字列。{key} 記法で context を参照可能
        task_type   : str  TaskType の value（デフォルト: "default"）
        output_key  : str  AI 回答を context に保存するキー（デフォルト: "ai_response"）
    """

    def __init__(self, router: Any | None = None) -> None:
        self._router = router

    @property
    def step_type(self) -> str:
        return "ai_task"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        if self._router is None:
            return StepResult(success=False, error="AIRouter が未注入です")
        try:
            from src.ai.task import AITask, TaskType

            cfg       = step.config
            prompt    = cfg.get("prompt", "").format(**status.context)
            task_type_str = cfg.get("task_type", "default")
            try:
                task_type = TaskType(task_type_str)
            except ValueError:
                task_type = TaskType.DEFAULT

            task = AITask(prompt=prompt, task_type=task_type)
            resp = self._router.route(task)

            if not resp.ok:
                return StepResult(success=False, error=resp.error or "AIRouter エラー")

            output_key = cfg.get("output_key", "ai_response")
            status.context[output_key] = resp.content

            return StepResult(
                success=True,
                output={
                    "content":  resp.content,
                    "provider": resp.provider,
                    "model":    resp.model,
                },
            )
        except Exception as exc:
            return StepResult(success=False, error=str(exc))
