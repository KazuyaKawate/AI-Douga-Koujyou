"""BaseFactoryMemory — JSON ファイルベースの Factory 記憶基盤。

Note/Writing/Video等すべてのFactory Memoryが継承する。

ファイル構造（data/{factory_name}_memory.json）:
{
  "entries": [
    {"created_at": "2026-06-28T...", ...}
  ],
  "updated_at": "2026-06-28T..."
}
"""
from __future__ import annotations

import json
from abc import ABC
from datetime import datetime
from pathlib import Path


class BaseFactoryMemory(ABC):
    """
    JSON ファイルベースの Factory 記憶基盤。

    サブクラス実装規約:
        - コンストラクタで super().__init__(path) を呼ぶ
        - add_entry() に渡す dict のスキーマはサブクラスが定義する
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 公開インターフェース
    # ------------------------------------------------------------------

    def load(self) -> dict:
        """メモリ全体を dict で返す。ファイルがなければ空の初期値を返す。"""
        if not self._path.exists():
            return {"entries": [], "updated_at": None}
        try:
            with open(self._path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"entries": [], "updated_at": None}

    def save(self, data: dict) -> None:
        """data を JSON ファイルに書き込む。"""
        data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_entry(self, entry: dict) -> None:
        """エントリを1件追加して保存する。created_at を自動付与する。"""
        data = self.load()
        entry.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
        data["entries"].append(entry)
        self.save(data)

    def get_recent(self, n: int = 10) -> list[dict]:
        """最新 n 件のエントリを返す（新しい順）。"""
        data = self.load()
        entries = data.get("entries", [])
        return list(reversed(entries[-n:])) if entries else []

    def count(self) -> int:
        """登録済みエントリ数を返す。"""
        return len(self.load().get("entries", []))

    def clear(self) -> None:
        """全エントリを削除する（テスト用）。"""
        self.save({"entries": []})
