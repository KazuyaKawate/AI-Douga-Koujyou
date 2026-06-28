from __future__ import annotations
from typing import TYPE_CHECKING, Any

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


class InboxPollExecutor(BaseStepExecutor):
    """
    InboxPoller.poll_once() を呼び出すExecutor。

    config フィールド:
        output_key : str  ポーリング件数を context に保存するキー（デフォルト: "polled_count"）
    """

    def __init__(self, poller: Any | None = None) -> None:
        self._poller = poller

    @property
    def step_type(self) -> str:
        return "inbox_poll"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        if self._poller is None:
            return StepResult(success=False, error="InboxPoller が未注入です")
        try:
            count      = self._poller.poll_once()
            output_key = step.config.get("output_key", "polled_count")
            status.context[output_key] = count
            return StepResult(success=True, output={"polled_count": count})
        except Exception as exc:
            return StepResult(success=False, error=str(exc))
