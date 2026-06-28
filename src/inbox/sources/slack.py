from __future__ import annotations
from ..models import InboxEntry
from .base import BaseInboxSource


class SlackInboxSource(BaseInboxSource):
    """
    Slack Events API 経由のInboxソース（将来実装）。

    想定フロー:
        Slack App メンション / コマンド → Events API → Factory_Inbox
    実装時の参考:
        slack-sdk (slack_bolt) を使い Event Subscription を設定する。
        bot_token / signing_secret は workspace_local.json で管理。
        app_mention イベントを InboxEntry として取り込む構成を検討。
    """

    @property
    def source_name(self) -> str:
        return "slack"

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
