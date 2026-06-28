from __future__ import annotations
from typing import TYPE_CHECKING

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


class NotificationExecutor(BaseStepExecutor):
    """
    通知送信Executor（将来実装）。

    実装時の参考:
        config["channel"] で通知先（slack / email / line）を指定し、
        config["message_template"] に {context_key} 記法でメッセージを組み立てる。
        slack_webhook_url 等は workspace_local.json で管理すること。
    """

    @property
    def step_type(self) -> str:
        return "notification"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        return StepResult(success=False, error="未実装: NotificationExecutor")
