from __future__ import annotations
from datetime import datetime
from typing import Optional

from .base import BaseTrigger


class CronTrigger(BaseTrigger):
    """
    Cron 式でスケジューリングするトリガー（将来実装）。

    実装時の参考:
        croniter ライブラリを使い、cron_expression から
        next_fire_at() を計算する。
        例: "0 9 * * 1-5" → 平日 9:00 に発火。
        timezone 対応も検討すること。
    """

    @property
    def trigger_name(self) -> str:
        return "cron"

    def should_fire(self) -> bool:
        return False  # 未実装

    def on_fired(self) -> None:
        pass  # 未実装

    def next_fire_at(self) -> Optional[datetime]:
        return None  # 未実装
