from __future__ import annotations
from datetime import datetime
from typing import Optional

from .base import BaseTrigger


class WebhookTrigger(BaseTrigger):
    """
    外部 Webhook を受信して発火するトリガー（将来実装）。

    実装時の参考:
        FastAPI / Flask でエンドポイントを立て、
        POST を受信したら内部フラグを True にする。
        Scheduler のループが should_fire() で検知して _tick() を実行する。
        認証は Bearer Token / HMAC 署名を検討すること。
    """

    @property
    def trigger_name(self) -> str:
        return "webhook"

    def should_fire(self) -> bool:
        return False  # 未実装

    def on_fired(self) -> None:
        pass  # 未実装

    def next_fire_at(self) -> Optional[datetime]:
        return None  # 発火タイミングが外部依存のため不定
