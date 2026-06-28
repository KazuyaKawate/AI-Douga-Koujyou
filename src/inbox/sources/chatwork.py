from __future__ import annotations
from ..models import InboxEntry
from .base import BaseInboxSource


class ChatworkInboxSource(BaseInboxSource):
    """
    Chatwork API 経由のInboxソース（将来実装）。

    想定フロー:
        Chatwork Bot → Webhook / ポーリング → Factory_Inbox
    実装時の参考:
        chatwork-client ライブラリまたは requests で REST API を呼ぶ。
        api_token は workspace_local.json で管理。
        メンション付きメッセージを InboxEntry として取り込む構成を検討。
    """

    @property
    def source_name(self) -> str:
        return "chatwork"

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
