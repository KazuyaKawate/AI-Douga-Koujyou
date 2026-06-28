from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable


class EventType(str, Enum):
    """Orchestrator が発火するイベント種別。"""
    WORKFLOW_STARTED   = "workflow_started"
    WORKFLOW_FINISHED  = "workflow_finished"
    WORKFLOW_FAILED    = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    WORKFLOW_PAUSED    = "workflow_paused"
    WORKFLOW_RESUMED   = "workflow_resumed"
    SNAPSHOT_CREATED   = "snapshot_created"
    MEMORY_UPDATED     = "memory_updated"


@dataclass
class Event:
    """イベントペイロード。EventBus を通じて配信される。"""

    event_type: EventType
    payload:    dict = field(default_factory=dict)
    timestamp:  str  = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )


class EventBus:
    """
    同期型イベントバス。

    subscribe() でコールバックを登録し、publish() でイベントを配信する。
    ハンドラの例外はイベント配信全体を止めない（例外を内部で握りつぶす）。
    イベント履歴は最大 _MAX_HISTORY 件を保持する。
    """

    _MAX_HISTORY = 200

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Callable[[Event], None]]] = defaultdict(list)
        self._history:  list[Event] = []

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """指定イベント種別のハンドラを登録する。"""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> bool:
        """登録済みハンドラを解除する。見つからなければ False を返す。"""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            return True
        return False

    def publish(self, event: Event) -> None:
        """イベントを全登録ハンドラに同期配信し、履歴に追記する。"""
        self._history.append(event)
        if len(self._history) > self._MAX_HISTORY:
            self._history = self._history[-self._MAX_HISTORY:]
        for handler in list(self._handlers.get(event.event_type, [])):
            try:
                handler(event)
            except Exception:
                pass

    def get_history(self, limit: int = 50) -> list[Event]:
        """最新 limit 件のイベント履歴を返す。"""
        return list(self._history[-limit:])
