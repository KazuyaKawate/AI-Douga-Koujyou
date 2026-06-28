from __future__ import annotations
from typing import TYPE_CHECKING, Any

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


class QueuePushExecutor(BaseStepExecutor):
    """
    TaskQueue.put() を呼び出すExecutor。

    config フィールド:
        prompt_from_context : str  context から prompt を取得するキー（優先）
        prompt              : str  直接指定する prompt 文字列
        task_type           : str  InboxEntry.task_type（デフォルト: "default"）
        source_name         : str  InboxEntry.source_name（デフォルト: "workflow"）
    """

    def __init__(self, queue: Any | None = None) -> None:
        self._queue = queue

    @property
    def step_type(self) -> str:
        return "queue_push"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        if self._queue is None:
            return StepResult(success=False, error="TaskQueue が未注入です")
        try:
            from src.inbox.models import InboxEntry

            cfg    = step.config
            if "prompt_from_context" in cfg:
                prompt = str(status.context.get(cfg["prompt_from_context"], ""))
            else:
                prompt = cfg.get("prompt", "")

            entry = InboxEntry(
                prompt=prompt,
                task_type=cfg.get("task_type", "default"),
                source_name=cfg.get("source_name", "workflow"),
            )
            self._queue.put(entry)
            return StepResult(success=True, output={"entry_id": entry.id})
        except Exception as exc:
            return StepResult(success=False, error=str(exc))
