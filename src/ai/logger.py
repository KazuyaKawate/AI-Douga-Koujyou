from __future__ import annotations
import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    """1リクエスト分のログレコード。"""
    timestamp:    datetime.datetime
    task_type:    str
    provider:     str
    duration_ms:  int
    ok:           bool
    input_tokens:  int | None = None   # 実API実装後に populated
    output_tokens: int | None = None   # 実API実装後に populated
    error:        str | None = None
    metadata:     dict | None = field(default=None)


class BaseRouterLogger(ABC):
    """
    ルーターログの基底インターフェース。

    実装例（将来）:
        class SheetsLogger(BaseRouterLogger): ...
        class SQLiteLogger(BaseRouterLogger): ...
        class PostgreSQLLogger(BaseRouterLogger): ...
    """

    @abstractmethod
    def log(self, entry: LogEntry) -> None:
        """ログエントリを永続化する。"""
        ...

    def close(self) -> None:
        """接続・バッファのクリーンアップ。必要な実装クラスでオーバーライドする。"""


class NullLogger(BaseRouterLogger):
    """デフォルトの no-op ロガー。実装クラスに差し替えるまでの代替。"""

    def log(self, entry: LogEntry) -> None:
        pass
