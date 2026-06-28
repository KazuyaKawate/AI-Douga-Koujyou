"""BaseFactoryAnalyzer — JSON ファイルベースの Factory 統計基盤。

Note/Writing/Video等すべてのFactory Analyzerが継承する。

ファイル構造（data/{factory_name}_stats.json）:
{
  "updated_at": "2026-06-28T...",
  ... (サブクラスが定義するフィールド)
}
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path


class BaseFactoryAnalyzer(ABC):
    """
    JSON ファイルベースの Factory 統計基盤。

    サブクラス実装規約:
        - コンストラクタで super().__init__(path) を呼ぶ
        - default_stats() を実装してデフォルト値を返す
        - update_stats(result) を実装して成果物1件分の統計を更新する
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 公開インターフェース
    # ------------------------------------------------------------------

    def load_stats(self) -> dict:
        """統計 dict を返す。ファイルがなければデフォルト値を返す。"""
        if not self._path.exists():
            return self.default_stats()
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            # デフォルト値にない新フィールドは追加された際に補完する
            defaults = self.default_stats()
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
        except (json.JSONDecodeError, OSError):
            return self.default_stats()

    def save_stats(self, stats: dict) -> None:
        """統計 dict を JSON ファイルに書き込む。"""
        stats["updated_at"] = datetime.now().isoformat(timespec="seconds")
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

    def reset_stats(self) -> None:
        """統計をデフォルト値にリセットする（テスト用）。"""
        self.save_stats(self.default_stats())

    # ------------------------------------------------------------------
    # サブクラスが実装するフック
    # ------------------------------------------------------------------

    @abstractmethod
    def default_stats(self) -> dict:
        """ファイルが存在しない場合に返すデフォルト統計 dict。"""
        ...

    @abstractmethod
    def update_stats(self, result: dict) -> dict:
        """
        成果物1件分のデータ（result）で統計を更新して保存し、更新後の dict を返す。

        Args:
            result: Executor が status.context に書き込んだ成果物の dict

        Returns:
            更新後の統計 dict
        """
        ...
