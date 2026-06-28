from __future__ import annotations
from datetime import datetime
from typing import Optional

from .base import BaseTrigger


class StartupTrigger(BaseTrigger):
    """
    スケジューラー起動時に一度だけ発火するトリガー（将来実装）。

    実装時の参考:
        should_fire() はスケジューラー起動直後の1回目のみ True を返す。
        on_fired() でフラグを立て、以降は False を返す。
        InitTask（初期化処理）を自動実行する用途向け。
    """

    @property
    def trigger_name(self) -> str:
        return "startup"

    def should_fire(self) -> bool:
        return False  # 未実装

    def on_fired(self) -> None:
        pass  # 未実装

    def next_fire_at(self) -> Optional[datetime]:
        return None  # 未実装
