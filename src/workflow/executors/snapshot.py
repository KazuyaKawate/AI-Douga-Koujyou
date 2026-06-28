from __future__ import annotations
from typing import TYPE_CHECKING, Any

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


class SnapshotExecutor(BaseStepExecutor):
    """
    SnapshotBuilder.save() を呼び出すExecutor。

    config フィールド:
        なし（snapshot_builder.save() は引数なしで呼べる想定）
    """

    def __init__(self, snapshot_builder: Any | None = None) -> None:
        self._snapshot_builder = snapshot_builder

    @property
    def step_type(self) -> str:
        return "snapshot"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        if self._snapshot_builder is None:
            return StepResult(success=False, error="SnapshotBuilder が未注入です")
        try:
            self._snapshot_builder.save()
            return StepResult(success=True, output={"saved": True})
        except Exception as exc:
            return StepResult(success=False, error=str(exc))
