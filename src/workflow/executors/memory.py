from __future__ import annotations
from typing import TYPE_CHECKING, Any

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


class MemoryUpdateExecutor(BaseStepExecutor):
    """
    BaseMemoryProvider.save() を呼び出すExecutor。

    config フィールド:
        key                 : str  保存するメモリキー
        value_from_context  : str  context から値を取得するキー（優先）
        value               : str  直接指定する値
        scope               : str  MemoryScope の value（デフォルト: "session"）
    """

    def __init__(self, memory: Any | None = None) -> None:
        self._memory = memory

    @property
    def step_type(self) -> str:
        return "memory_update"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        if self._memory is None:
            return StepResult(success=False, error="MemoryProvider が未注入です")
        try:
            from src.ai.memory import MemoryScope

            cfg       = step.config
            key       = cfg.get("key", "workflow_result")
            scope_str = cfg.get("scope", "session")
            try:
                scope = MemoryScope(scope_str)
            except ValueError:
                scope = MemoryScope.SESSION

            if "value_from_context" in cfg:
                value = str(status.context.get(cfg["value_from_context"], ""))
            else:
                value = str(cfg.get("value", ""))

            self._memory.save(key=key, value=value, scope=scope)
            return StepResult(success=True, output={"key": key, "scope": scope_str})
        except Exception as exc:
            return StepResult(success=False, error=str(exc))
