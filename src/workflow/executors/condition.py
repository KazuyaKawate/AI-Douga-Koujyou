from __future__ import annotations
from typing import TYPE_CHECKING

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


class ConditionExecutor(BaseStepExecutor):
    """
    条件分岐Executor（将来実装）。

    実装時の参考:
        config["expression"] に Python 式またはルール記述を持ち、
        status.context の値を評価して次ステップの実行可否を制御する。
        例: {"expression": "polled_count > 0"} → polled_count が 0 なら後続をスキップ
    """

    @property
    def step_type(self) -> str:
        return "condition"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        return StepResult(success=False, error="未実装: ConditionExecutor")
