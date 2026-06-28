from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


@dataclass
class StepResult:
    """
    BaseStepExecutor.execute() の返り値 DTO。

    例外を外に投げず、失敗は success=False + error で表現する。
    wait_for_approval=True のとき WorkflowRunner は WAITING_APPROVAL 状態に入る。
    output に格納した値は WorkflowStatus.steps[step_id].output に記録される。
    """

    success:           bool
    output:            dict = field(default_factory=dict)
    error:             str | None = None
    wait_for_approval: bool = False


class BaseStepExecutor(ABC):
    """
    ステップ実行インターフェース。

    WorkflowRunner は EXECUTOR_REGISTRY を通じてこの ABC のみに依存する。
    「どう実行するか」はサブクラスに閉じること。

    実装ルール:
        - execute() は例外を外に投げない。失敗は StepResult(success=False, error=...) で返す
        - 副作用（Memory/Snapshot書き込み）は allow_write 設定に従うこと
        - コンストラクタで受け取る依存は Optional にし、None 時は success=False を返す

    新規 Executor 追加手順:
        1. このクラスを継承したクラスを executors/ 以下に作成する
        2. step_type プロパティと execute() を実装する
        3. executors/__init__.py の EXECUTOR_REGISTRY に登録する
        4. StepType Enum にエントリを追加する
    """

    @property
    @abstractmethod
    def step_type(self) -> str:
        """EXECUTOR_REGISTRY のキー（StepType.value と一致させること）。"""
        ...

    @abstractmethod
    def execute(
        self,
        step: "WorkflowStep",
        status: "WorkflowStatus",
    ) -> StepResult:
        """
        ステップを実行し StepResult を返す。例外を外に投げない。

        step.config に実行パラメータが入っている。
        status.context を読み書きして steps 間でデータを受け渡せる。
        """
        ...
