from __future__ import annotations
from datetime import datetime
from typing import Optional

from .base import BaseTrigger


class CalendarTrigger(BaseTrigger):
    """
    カレンダーベースのスケジューリングトリガー（将来実装）。

    実装時の参考:
        Google Calendar API や iCal (.ics) を参照し、
        登録されたイベント時刻に発火する。
        例: 毎週月曜 10:00 のミーティング前に自動で資料を生成する。
        credentials は workspace_local.json で管理すること。
    """

    @property
    def trigger_name(self) -> str:
        return "calendar"

    def should_fire(self) -> bool:
        return False  # 未実装

    def on_fired(self) -> None:
        pass  # 未実装

    def next_fire_at(self) -> Optional[datetime]:
        return None  # 未実装
