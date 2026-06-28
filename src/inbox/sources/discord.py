from __future__ import annotations
from ..models import InboxEntry
from .base import BaseInboxSource


class DiscordInboxSource(BaseInboxSource):
    """
    Discord Bot 経由のInboxソース（将来実装）。

    想定フロー:
        Discord コマンド / メンション → Bot → Factory_Inbox
    実装時の参考:
        discord.py を使いスラッシュコマンドを定義する。
        bot_token は workspace_local.json で管理。
        特定チャンネルへのメッセージを InboxEntry として取り込む構成を検討。
    """

    @property
    def source_name(self) -> str:
        return "discord"

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
