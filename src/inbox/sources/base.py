from __future__ import annotations
from abc import ABC, abstractmethod

from ..models import InboxEntry


class BaseInboxSource(ABC):
    """
    Inbox ソースの基底インターフェース。

    新しいソースを追加する手順:
        1. このクラスを継承したクラスを sources/ 以下に作成する
        2. 抽象メソッドをすべて実装する
        3. sources/__init__.py の SOURCE_REGISTRY に登録する

    InboxPoller / TaskQueue / TaskRunner はこのインターフェースのみに依存する。
    ソース固有の実装はサブクラスに閉じること。

    将来追加予定:
        ChatGPTInboxSource   - ChatGPT Plugin / Actions 経由
        LINEInboxSource      - LINE Messaging API 経由
        ChatworkInboxSource  - Chatwork API 経由
        DiscordInboxSource   - Discord Bot 経由
        SlackInboxSource     - Slack Events API 経由
        RESTAPIInboxSource   - 汎用 REST Webhook 経由
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """ソース識別子（例: "google_sheets", "chatgpt"）。InboxEntry.source_name に設定される。"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """このソースが利用可能かを返す。設定不備・未実装の場合は False。"""
        ...

    @abstractmethod
    def fetch_pending(self, max_batch: int) -> list[InboxEntry]:
        """
        status="pending" のエントリを最大 max_batch 件取得して返す。

        - この呼び出しはエントリの status を変更しない
        - status 更新は mark_processing() / mark_done() / mark_error() で行う
        - 取得できない場合は空リストを返す（例外を送出しない）
        """
        ...

    @abstractmethod
    def mark_processing(self, entry_id: str) -> None:
        """
        指定エントリの status を "processing" に更新する。

        allow_write=False 時は dry-run ログのみ出力し、実際の更新は行わない。
        """
        ...

    @abstractmethod
    def mark_done(self, entry_id: str) -> None:
        """
        指定エントリの status を "done" に更新する。

        allow_write=False 時は dry-run ログのみ出力し、実際の更新は行わない。
        """
        ...

    @abstractmethod
    def mark_error(self, entry_id: str, message: str) -> None:
        """
        指定エントリの status を "error" に更新し、エラーメッセージを記録する。

        allow_write=False 時は dry-run ログのみ出力し、実際の更新は行わない。
        """
        ...
