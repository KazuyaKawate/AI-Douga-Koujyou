from __future__ import annotations
from ..models import InboxEntry
from .base import BaseInboxSource


class LINEInboxSource(BaseInboxSource):
    """
    LINE Messaging API 経由のInboxソース（将来実装）。

    想定フロー:
        LINE Bot → Webhook → Factory_Inbox
    実装時の参考:
        line-bot-sdk-python を使い、Webhook イベントを受信して
        InboxEntry に変換する。
        channel_access_token / channel_secret は workspace_local.json で管理。
    """

    @property
    def source_name(self) -> str:
        return "line"

    def is_available(self) -> bool:
        return False  # 未実装

    def fetch_pending(self, max_batch: int) -> list[InboxEntry]:
        return []

    def mark_processing(self, entry_id: str) -> None:
        pass

    def mark_done(self, entry_id: str) -> None:
        pass

    def mark_error(self, entry_id: str, message: str) -> None:
        pass
