"""BaseFactoryExecutor — Factory専用Executorの共通基底クラス。

すべてのFactory（Note/Writing/Video/Research等）のExecutorは
このクラスを継承する。

設計:
  - router を受け取り、スタブモード/AIモードを自動切り替え
  - execute() が共通例外ハンドリングを担い、サブクラスは _execute() のみ実装
  - has_router プロパティでモード判定を統一
"""
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from src.workflow.executors.base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


class BaseFactoryExecutor(BaseStepExecutor):
    """
    Factory Executor 基底クラス。

    サブクラス実装規約:
        - step_type プロパティを実装する
        - _execute() を実装する（例外は内側で処理してよい）
        - スタブモード: self.has_router が False のとき固定値を返す
        - AIモード:    self._router.complete(task) を呼ぶ
    """

    def __init__(self, router: Any | None = None) -> None:
        self._router = router

    @property
    def has_router(self) -> bool:
        """Trueなら AI Router が注入されている（AIモード）。"""
        return self._router is not None

    def execute(
        self,
        step: "WorkflowStep",
        status: "WorkflowStatus",
    ) -> StepResult:
        """共通例外ラッパー。サブクラスは _execute() を実装する。"""
        try:
            return self._execute(step, status)
        except Exception as exc:
            return StepResult(success=False, error=f"{self.__class__.__name__}: {exc}")

    @abstractmethod
    def _execute(
        self,
        step: "WorkflowStep",
        status: "WorkflowStatus",
    ) -> StepResult:
        """実際の処理を実装するフック。例外を外に出してよい（execute()が捕捉する）。"""
        ...
