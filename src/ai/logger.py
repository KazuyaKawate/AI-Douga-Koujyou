from __future__ import annotations
import datetime
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ---- データモデル -------------------------------------------------------

@dataclass
class LogEntry:
    """1リクエスト分のログレコード。全フィールドはデフォルト値付きで将来の変更に対応。"""

    # 識別
    request_id:        str                    = field(default_factory=lambda: str(uuid.uuid4()))
    parent_request_id: str | None             = None

    # タイミング
    timestamp:         datetime.datetime      = field(default_factory=datetime.datetime.now)

    # ルーティング
    task_type:         str                    = ""
    provider:          str                    = ""
    model:             str                    = ""

    # 性能
    latency_ms:        int                    = 0

    # トークン（実API実装後に populated）
    input_tokens:      int | None             = None
    output_tokens:     int | None             = None

    # コスト（実API実装後に populated）
    cost_usd:          float | None           = None

    # 結果
    success:           bool                   = True
    error_message:     str | None             = None

    # 拡張（将来項目追加はここへ）
    metadata:          dict[str, Any] | None  = field(default=None)


# ---- 基底インターフェース -------------------------------------------------

class BaseRouterLogger(ABC):
    """
    ルーターログの基底インターフェース。

    将来の実装クラス例:
        class SheetsRouterLogger(BaseRouterLogger): ...
        class SQLiteLogger(BaseRouterLogger):       ...
        class JSONFileLogger(BaseRouterLogger):     ...
        class PostgreSQLLogger(BaseRouterLogger):   ...
    """

    @abstractmethod
    def log(self, entry: LogEntry) -> None:
        """ログエントリを永続化する。"""
        ...

    def close(self) -> None:
        """接続・バッファのクリーンアップ。必要な実装クラスでオーバーライドする。"""


# ---- デフォルト実装 -------------------------------------------------------

class NullLogger(BaseRouterLogger):
    """デフォルトの no-op ロガー。実装クラスに差し替えるまでの代替。"""

    def log(self, entry: LogEntry) -> None:
        pass


# ---- 将来実装スタブ --------------------------------------------------------
#
# Google Sheets を Claude のコンテキスト制限対策・外部記憶として使う設計。
# 現時点では保存処理は未実装。インターフェースとシート構造定義のみ。
#
# 想定スプレッドシート構成:
#
#   AI_Requests  — リクエスト追跡（親子関係で連鎖呼び出しを可視化）
#     request_id | parent_request_id | task_type | provider
#     | status | created_at | completed_at
#
#   AI_Logs  — 性能ログ（コスト・レイテンシ集計用）
#     request_id | provider | model | latency_ms
#     | input_tokens | output_tokens | cost_usd | success | error_message
#
#   AI_Decisions  — 判断記録（Claude外部記憶: なぜその判断をしたかを残す）
#     request_id | decision | reason | approved_by_user | created_at
#
#   AI_Memory  — 永続キーバリューストア（Claude外部記憶: セッション跨ぎの状態保持）
#     key | value | scope | updated_at
#

class SheetsRouterLogger(BaseRouterLogger):
    """
    Google Sheets ロガー（スタブ）。

    将来の接続先: config/workspace_local.json の spreadsheet_id を使用。
    認証: Workspace Sync と同じ service_account または OAuth 認証を流用予定。
    書き込み: gspread.Worksheet.append_row() を使用。

    実装時の注意:
        - allow_write フラグを設け、dry-run モードをデフォルトにすること
        - API レート制限を考慮してバッチ書き込みを検討すること
        - credentials は絶対にコードに埋め込まないこと
    """

    # シート名定数
    SHEET_REQUESTS  = "AI_Requests"
    SHEET_LOGS      = "AI_Logs"
    SHEET_DECISIONS = "AI_Decisions"
    SHEET_MEMORY    = "AI_Memory"

    # 列定義（将来の append_row の引数順序）
    COLUMNS_REQUESTS  = [
        "request_id", "parent_request_id", "task_type", "provider",
        "status", "created_at", "completed_at",
    ]
    COLUMNS_LOGS      = [
        "request_id", "provider", "model", "latency_ms",
        "input_tokens", "output_tokens", "cost_usd", "success", "error_message",
    ]
    COLUMNS_DECISIONS = [
        "request_id", "decision", "reason", "approved_by_user", "created_at",
    ]
    COLUMNS_MEMORY    = ["key", "value", "scope", "updated_at"]

    def __init__(self, spreadsheet_id: str, credentials_path: str) -> None:
        # スタブ: 将来ここで gspread クライアントを初期化する
        # self._client = gspread.service_account(filename=credentials_path)
        # self._ss     = self._client.open_by_key(spreadsheet_id)
        self._spreadsheet_id   = spreadsheet_id
        self._credentials_path = credentials_path

    # ---- BaseRouterLogger 実装 -------------------------------------------

    def log(self, entry: LogEntry) -> None:
        """
        スタブ: AI_Requests と AI_Logs の両シートへ行を追記する。

        将来実装イメージ:
            ws = self._ss.worksheet(self.SHEET_REQUESTS)
            ws.append_row([
                entry.request_id, entry.parent_request_id, entry.task_type,
                entry.provider, "completed",
                entry.timestamp.isoformat(), datetime.datetime.now().isoformat(),
            ])
            ws = self._ss.worksheet(self.SHEET_LOGS)
            ws.append_row([
                entry.request_id, entry.provider, entry.model, entry.latency_ms,
                entry.input_tokens, entry.output_tokens, entry.cost_usd,
                entry.success, entry.error_message,
            ])
        """

    # ---- 外部記憶 API -------------------------------------------------------

    def log_decision(
        self,
        request_id: str,
        decision: str,
        reason: str,
        approved_by_user: bool = False,
    ) -> None:
        """
        スタブ: AI_Decisions シートへ判断記録を追記する。

        用途: Claude が「なぜその判断をしたか」を外部へ残し、
              セッション再開時に読み返せるようにする。
        """

    def memory_set(self, key: str, value: str, scope: str = "global") -> None:
        """
        スタブ: AI_Memory シートへ key-value をアップサート（upsert）する。

        用途: セッション跨ぎで保持すべき状態を Google Sheets に永続化する。
              scope で "project" / "session" / "global" を使い分ける。
        """

    def memory_get(self, key: str, scope: str = "global") -> str | None:
        """
        スタブ: AI_Memory シートから key を検索して value を返す。

        将来実装イメージ:
            ws = self._ss.worksheet(self.SHEET_MEMORY)
            records = ws.get_all_records()
            for row in records:
                if row["key"] == key and row["scope"] == scope:
                    return str(row["value"])
            return None
        """
        return None
