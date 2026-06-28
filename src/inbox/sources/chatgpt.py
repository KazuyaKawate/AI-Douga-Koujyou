from __future__ import annotations
from ..models import InboxEntry
from .base import BaseInboxSource


class ChatGPTInboxSource(BaseInboxSource):
    """
    ChatGPT Plugin / Actions 経由のInboxソース（将来実装）。

    想定フロー:
        ChatGPT Action → REST Webhook → Factory_Inbox テーブル / キュー
    実装時の参考:
        OpenAI GPT Actions で HTTP POST エンドポイントを定義し、
        Factory 側の REST API に転送する構成を検討すること。
    """

    @property
    def source_name(self) -> str:
        return "chatgpt"

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
