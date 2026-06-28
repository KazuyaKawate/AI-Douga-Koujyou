from __future__ import annotations
from typing import TYPE_CHECKING

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


class HumanApprovalExecutor(BaseStepExecutor):
    """
    Human Approval 待ちを開始するExecutor。

    このExecutor は wait_for_approval=True を返すだけで、承認待ちを開始する。
    実際の承認/却下は WorkflowRunner.approve() / reject() から行う。

    config フィールド:
        message : str  承認者に表示するメッセージ（Dashboard 表示予定）
    """

    @property
    def step_type(self) -> str:
        return "human_approval"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        message = step.config.get("message", "承認が必要です")
        return StepResult(
            success=True,
            output={"message": message},
            wait_for_approval=True,
        )
