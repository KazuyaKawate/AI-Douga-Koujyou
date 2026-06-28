from __future__ import annotations
from datetime import datetime
from typing import Optional

from .base import BaseTrigger


class ManualTrigger(BaseTrigger):
    """
    外部コードから fire() を呼んで発火するトリガー（将来実装）。

    FactoryScheduler.run_once() は Trigger を経由せず _tick() を直接呼ぶため、
    このトリガーは「ループ中に外部から発火させる」用途向け。

    使い方（将来）:
        trigger = ManualTrigger()
        scheduler = FactoryScheduler(..., trigger=trigger)
        scheduler.start()
        # 別スレッドから発火
        trigger.fire()
    """

    def __init__(self) -> None:
        self._pending: bool = False

    @property
    def trigger_name(self) -> str:
        return "manual"

    def should_fire(self) -> bool:
        return self._pending

    def on_fired(self) -> None:
        self._pending = False

    def next_fire_at(self) -> Optional[datetime]:
        return None  # 手動発火のため不定

    def fire(self) -> None:
        """外部から呼んで発火をリクエストする（将来実装時に使用）。"""
        self._pending = True
