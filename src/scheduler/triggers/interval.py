from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional

from .base import BaseTrigger


class IntervalTrigger(BaseTrigger):
    """
    一定間隔で発火するトリガー。

    初回は即座に発火する（last_fired_at が None のため）。
    以降は interval_sec 経過ごとに should_fire() が True を返す。

    使い方:
        trigger = IntervalTrigger(interval_sec=60)
        scheduler = FactoryScheduler(poller=..., runner=..., trigger=trigger, ...)
    """

    def __init__(self, interval_sec: int) -> None:
        if interval_sec <= 0:
            raise ValueError(f"interval_sec は正の整数が必要です: {interval_sec}")
        self._interval_sec:  int                   = interval_sec
        self._last_fired_at: Optional[datetime]    = None

    # ---- BaseTrigger 実装 ------------------------------------------

    @property
    def trigger_name(self) -> str:
        return "interval"

    def should_fire(self) -> bool:
        if self._last_fired_at is None:
            return True  # 初回は即座に発火
        elapsed = (datetime.now() - self._last_fired_at).total_seconds()
        return elapsed >= self._interval_sec

    def on_fired(self) -> None:
        self._last_fired_at = datetime.now()

    def next_fire_at(self) -> Optional[datetime]:
        if self._last_fired_at is None:
            return datetime.now()
        return self._last_fired_at + timedelta(seconds=self._interval_sec)

    # ---- 追加プロパティ --------------------------------------------

    @property
    def interval_sec(self) -> int:
        return self._interval_sec

    @property
    def last_fired_at(self) -> Optional[datetime]:
        return self._last_fired_at
