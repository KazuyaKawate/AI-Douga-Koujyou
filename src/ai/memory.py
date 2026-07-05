from __future__ import annotations
import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---- 列挙型 -----------------------------------------------------------

from src.utils.json_store import save_json_atomic
class MemoryScope(str, Enum):
    """AI が読み込む範囲。将来の実装でフィルタ条件に使う。"""
    GLOBAL  = "global"   # プロジェクト跨ぎ
    PROJECT = "project"  # 現在プロジェクト内
    SESSION = "session"  # 起動中のみ
    USER    = "user"     # ユーザー固有（マルチユーザー対応想定）


class TTL(str, Enum):
    """有効期限の種別。将来 expires_at の自動計算に使う。"""
    PERMANENT = "permanent"  # 永続
    SESSION   = "session"    # セッション終了まで
    HOURS_24  = "hours_24"   # 24時間
    DAYS_7    = "days_7"     # 7日


class MemoryKey(str, Enum):
    """扱うキー名の定義。タイポ防止・補完サポート用。"""
    CURRENT_PROJECT      = "current_project"
    CURRENT_PHASE        = "current_phase"
    CURRENT_TASK         = "current_task"
    APPROVED_SPEC        = "approved_spec"
    PENDING_TASK         = "pending_task"
    DECISION_HISTORY     = "decision_history"
    IMPORTANT_NOTES      = "important_notes"
    CONVERSATION_SUMMARY = "conversation_summary"
    LAST_ERROR           = "last_error"
    LAST_PROVIDER        = "last_provider"
    LAST_MODEL           = "last_model"
    SHARED_CONTEXT       = "shared_context"


# ---- データモデル -------------------------------------------------------

@dataclass
class MemoryEntry:
    """1エントリのデータモデル。"""

    key:        str
    value:      str

    # スコープ・有効期限
    scope:      MemoryScope           = MemoryScope.GLOBAL
    ttl:        TTL                   = TTL.PERMANENT
    expires_at: datetime.datetime | None = None     # 将来: set() 時に TTL から計算

    # 履歴管理
    version:    int                   = 1           # set() のたびにインクリメント

    # タイムスタンプ
    updated_at: datetime.datetime     = field(default_factory=datetime.datetime.now)

    # 拡張（将来項目追加はここへ）
    metadata:   dict[str, Any] | None = field(default=None)


# ---- 基底インターフェース -------------------------------------------------

class BaseMemoryProvider(ABC):
    """
    AI 共有記憶の基底インターフェース。

    将来の実装クラス例:
        class GoogleSheetsMemoryProvider(BaseMemoryProvider): ...
        class SQLiteMemoryProvider(BaseMemoryProvider):       ...
        class PostgreSQLMemoryProvider(BaseMemoryProvider):   ...
    """

    @abstractmethod
    def get(
        self,
        key: str,
        scope: MemoryScope = MemoryScope.GLOBAL,
    ) -> str | None:
        """指定 key の value を返す。存在しない場合は None。"""
        ...

    @abstractmethod
    def set(
        self,
        key: str,
        value: str,
        scope: MemoryScope = MemoryScope.GLOBAL,
        ttl: TTL = TTL.PERMANENT,
    ) -> None:
        """key を書き込む。同一 key が存在する場合は version をインクリメント。"""
        ...

    @abstractmethod
    def delete(
        self,
        key: str,
        scope: MemoryScope = MemoryScope.GLOBAL,
    ) -> None:
        """指定 key を削除する。存在しない場合は何もしない。"""
        ...

    @abstractmethod
    def get_all(
        self,
        scope: MemoryScope | None = None,
    ) -> list[MemoryEntry]:
        """全エントリを返す。scope 指定で絞り込み。"""
        ...

    def get_entry(
        self,
        key: str,
        scope: MemoryScope = MemoryScope.GLOBAL,
    ) -> MemoryEntry | None:
        """MemoryEntry ごと取得する。デフォルト実装は get_all から検索。"""
        for entry in self.get_all(scope):
            if entry.key == key and entry.scope == scope:
                return entry
        return None

    def count(self, scope: "MemoryScope | None" = None) -> int:
        """エントリ数を返す。scope 指定で絞り込み。"""
        return len(self.get_all(scope))

    def close(self) -> None:
        """接続・バッファのクリーンアップ。必要な実装クラスでオーバーライドする。"""


# ---- デフォルト実装 -------------------------------------------------------

class NullMemoryProvider(BaseMemoryProvider):
    """デフォルトの no-op 実装。オフライン・テスト時の代替。"""

    def get(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL) -> str | None:
        return None

    def set(
        self,
        key: str,
        value: str,
        scope: MemoryScope = MemoryScope.GLOBAL,
        ttl: TTL = TTL.PERMANENT,
    ) -> None:
        pass

    def delete(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL) -> None:
        pass

    def get_all(self, scope: MemoryScope | None = None) -> list[MemoryEntry]:
        return []


class InMemoryProvider(BaseMemoryProvider):
    """
    オンメモリの一時実装。テスト・開発用。

    セッション終了で消えるため、永続化が必要な場面では
    GoogleSheetsMemoryProvider / SQLiteMemoryProvider を使うこと。
    """

    def __init__(self) -> None:
        # (key, scope.value) → MemoryEntry
        self._store: dict[tuple[str, str], MemoryEntry] = {}

    def get(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL) -> str | None:
        entry = self._store.get((key, scope.value))
        return entry.value if entry else None

    def set(
        self,
        key: str,
        value: str,
        scope: MemoryScope = MemoryScope.GLOBAL,
        ttl: TTL = TTL.PERMANENT,
    ) -> None:
        store_key = (key, scope.value)
        existing  = self._store.get(store_key)
        version   = (existing.version + 1) if existing else 1
        self._store[store_key] = MemoryEntry(
            key=key,
            value=value,
            scope=scope,
            ttl=ttl,
            version=version,
            updated_at=datetime.datetime.now(),
        )

    def delete(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL) -> None:
        self._store.pop((key, scope.value), None)

    def get_all(self, scope: MemoryScope | None = None) -> list[MemoryEntry]:
        if scope is None:
            return list(self._store.values())
        return [e for e in self._store.values() if e.scope == scope]


class FileMemoryProvider(BaseMemoryProvider):
    """
    JSON ファイルへ永続化するメモリプロバイダー。

    デフォルト保存先: data/aios_memory.json
    InMemoryProvider の永続版として AIOS Kernel に注入する。
    マルチプロセス非対応 — Streamlit シングルプロセス前提。
    """

    DEFAULT_PATH = Path("data/aios_memory.json")

    def __init__(self, path: "Path | None" = None) -> None:
        self._path  = path or self.DEFAULT_PATH
        self._store: "dict[tuple[str, str], MemoryEntry]" = {}
        self._load()

    def get(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL) -> "str | None":
        entry = self._store.get((key, scope.value))
        return entry.value if entry else None

    def set(
        self,
        key: str,
        value: str,
        scope: MemoryScope = MemoryScope.GLOBAL,
        ttl: TTL = TTL.PERMANENT,
    ) -> None:
        store_key = (key, scope.value)
        existing  = self._store.get(store_key)
        version   = (existing.version + 1) if existing else 1
        self._store[store_key] = MemoryEntry(
            key=key,
            value=value,
            scope=scope,
            ttl=ttl,
            version=version,
            updated_at=datetime.datetime.now(),
        )
        self._flush()

    def delete(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL) -> None:
        self._store.pop((key, scope.value), None)
        self._flush()

    def get_all(self, scope: "MemoryScope | None" = None) -> "list[MemoryEntry]":
        if scope is None:
            return list(self._store.values())
        return [e for e in self._store.values() if e.scope == scope]

    def _flush(self) -> None:
        """_store を JSON ファイルへ書き出す。例外は無視する。"""
        try:
            import json
            self._path.parent.mkdir(parents=True, exist_ok=True)
            rows = [
                {
                    "key":        e.key,
                    "value":      e.value,
                    "scope":      e.scope.value,
                    "ttl":        e.ttl.value,
                    "version":    e.version,
                    "updated_at": e.updated_at.isoformat(),
                }
                for e in self._store.values()
            ]
            save_json_atomic(self._path, rows)
        except Exception:
            pass

    def _load(self) -> None:
        """起動時に JSON から _store を復元する。"""
        if not self._path.exists():
            return
        try:
            import json
            for row in json.loads(self._path.read_text(encoding="utf-8")):
                try:
                    scope = MemoryScope(row.get("scope", "global"))
                    ttl   = TTL(row.get("ttl", "permanent"))
                    entry = MemoryEntry(
                        key=row["key"],
                        value=row["value"],
                        scope=scope,
                        ttl=ttl,
                        version=int(row.get("version", 1)),
                        updated_at=datetime.datetime.fromisoformat(
                            row.get("updated_at", datetime.datetime.now().isoformat())
                        ),
                    )
                    self._store[(entry.key, entry.scope.value)] = entry
                except Exception:
                    continue
        except Exception:
            pass


# ---- 将来実装スタブ --------------------------------------------------------

class GoogleSheetsMemoryProvider(BaseMemoryProvider):
    """
    Google Sheets メモリプロバイダー（スタブ）。

    実装時の注意:
        - allow_write フラグを設け、dry-run をデフォルトにすること
        - 同一 key の upsert では version を +1 してから書き込むこと
        - API レート制限対策としてバッチ読み書きを検討すること
        - TTL が有効な場合、get() で expires_at を比較して失効判定を行うこと
        - credentials は絶対にコードに埋め込まないこと
    """

    SHEET_NAME = "AI_Memory"
    COLUMNS    = [
        "key", "value", "scope", "ttl",
        "version", "updated_at", "expires_at",
    ]

    def __init__(self, spreadsheet_id: str, credentials_path: str) -> None:
        # スタブ: 将来ここで gspread クライアントを初期化する
        # self._client = gspread.service_account(filename=credentials_path)
        # self._ws     = self._client.open_by_key(spreadsheet_id).worksheet(self.SHEET_NAME)
        self._spreadsheet_id   = spreadsheet_id
        self._credentials_path = credentials_path

    def get(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL) -> str | None:
        # スタブ: 将来 ws.get_all_records() から key+scope で検索して返す
        return None

    def set(
        self,
        key: str,
        value: str,
        scope: MemoryScope = MemoryScope.GLOBAL,
        ttl: TTL = TTL.PERMANENT,
    ) -> None:
        # スタブ: 将来 existing を検索 → version+1 で upsert する
        pass

    def delete(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL) -> None:
        # スタブ: 将来 ws.find() で行を特定して削除する
        pass

    def get_all(self, scope: MemoryScope | None = None) -> list[MemoryEntry]:
        # スタブ: 将来 ws.get_all_records() を MemoryEntry リストに変換して返す
        return []
