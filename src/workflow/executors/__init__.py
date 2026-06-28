from .base import BaseStepExecutor, StepResult
from .ai_task import AITaskExecutor
from .memory import MemoryUpdateExecutor
from .snapshot import SnapshotExecutor
from .approval import HumanApprovalExecutor
from .inbox_poll import InboxPollExecutor
from .queue_push import QueuePushExecutor
from .condition import ConditionExecutor
from .notification import NotificationExecutor

# StepType.value → Executor クラスのレジストリ。
# 新規 Executor 追加時はここと enums.StepType に登録する。
EXECUTOR_REGISTRY: dict[str, type[BaseStepExecutor]] = {
    "ai_task":        AITaskExecutor,
    "memory_update":  MemoryUpdateExecutor,
    "snapshot":       SnapshotExecutor,
    "human_approval": HumanApprovalExecutor,
    "inbox_poll":     InboxPollExecutor,
    "queue_push":     QueuePushExecutor,
    "condition":      ConditionExecutor,
    "notification":   NotificationExecutor,
}

__all__ = [
    "BaseStepExecutor",
    "StepResult",
    "AITaskExecutor",
    "MemoryUpdateExecutor",
    "SnapshotExecutor",
    "HumanApprovalExecutor",
    "InboxPollExecutor",
    "QueuePushExecutor",
    "ConditionExecutor",
    "NotificationExecutor",
    "EXECUTOR_REGISTRY",
]
