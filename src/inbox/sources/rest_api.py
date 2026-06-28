from __future__ import annotations
from ..models import InboxEntry
from .base import BaseInboxSource


class RESTAPIInboxSource(BaseInboxSource):
    """
    汎用 REST Webhook 経由のInboxソース（将来実装）。

    想定フロー:
        外部サービス → POST /inbox → Factory_Inbox キュー
    実装時の参考:
        FastAPI または Flask で /inbox エンドポイントを立て、
        受信した JSON を InboxEntry に変換してキューに投入する。
        認証は Bearer Token / HMAC 署名を検討すること。
        これにより ChatGPT・Zapier・IFTTT など任意のサービスと接続できる。
    """

    @property
    def source_name(self) -> str:
        return "rest_api"

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
