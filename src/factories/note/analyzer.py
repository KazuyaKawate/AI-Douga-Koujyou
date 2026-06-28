"""NoteAnalyzer — 記事の統計を JSON で集計・永続化する。

data/note_stats.json に統計を蓄積し、
Workflow の note_analyze ステップから呼ばれる。

将来の Writing/Video Factory も同様に BaseFactoryAnalyzer を継承する。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.factories.framework.analyzer import BaseFactoryAnalyzer
from src.factories.note.models import NoteStats

_DEFAULT_PATH = Path("data/note_stats.json")


class NoteAnalyzer(BaseFactoryAnalyzer):
    """
    Note Factory 専用 Analyzer。

    統計フィールド（note_stats.json）:
    {
      "articles_today":         int,
      "articles_this_month":    int,
      "waiting_publish":        int,
      "waiting_approval":       int,
      "published_total":        int,
      "total_word_count":       int,
      "avg_word_count":         float,
      "estimated_revenue_jpy":  int,
      "last_date":              str (YYYY-MM-DD, 日次リセット判定用),
      "last_month":             str (YYYY-MM, 月次リセット判定用),
      "updated_at":             str
    }
    """

    def __init__(self, path: Path | None = None, price_jpy: int = 500) -> None:
        super().__init__(path or _DEFAULT_PATH)
        self._price_jpy = price_jpy

    # ------------------------------------------------------------------
    # BaseFactoryAnalyzer 実装
    # ------------------------------------------------------------------

    def default_stats(self) -> dict:
        today = datetime.now()
        return {
            "articles_today":        0,
            "articles_this_month":   0,
            "waiting_publish":       0,
            "waiting_approval":      0,
            "published_total":       0,
            "total_word_count":      0,
            "avg_word_count":        0.0,
            "estimated_revenue_jpy": 0,
            "last_date":             today.strftime("%Y-%m-%d"),
            "last_month":            today.strftime("%Y-%m"),
            "updated_at":            None,
        }

    def update_stats(self, result: dict) -> dict:
        """
        記事1件分の result で統計を更新して保存する。

        result キー（executors.py の NotePublishExecutor が書き込む）:
          article_id, word_count, status, monetization_path
        """
        stats = self._apply_date_resets(self.load_stats())

        word_count = result.get("word_count", 0)
        monetization = result.get("monetization_path", "無料+CTA")

        stats["articles_today"]       += 1
        stats["articles_this_month"]  += 1
        stats["published_total"]      += 1
        stats["total_word_count"]     += word_count

        total = stats["published_total"]
        stats["avg_word_count"] = (
            round(stats["total_word_count"] / total, 1) if total else 0.0
        )

        if "有料" in monetization:
            stats["estimated_revenue_jpy"] += self._price_jpy

        self.save_stats(stats)
        return stats

    # ------------------------------------------------------------------
    # 追加ユーティリティ
    # ------------------------------------------------------------------

    def increment_waiting_approval(self) -> None:
        """承認待ち件数を +1 する。"""
        stats = self.load_stats()
        stats["waiting_approval"] = stats.get("waiting_approval", 0) + 1
        self.save_stats(stats)

    def decrement_waiting_approval(self) -> None:
        """承認待ち件数を -1 する（承認/却下後）。"""
        stats = self.load_stats()
        stats["waiting_approval"] = max(0, stats.get("waiting_approval", 0) - 1)
        self.save_stats(stats)

    def get_note_stats(self) -> NoteStats:
        """Dashboard 用 NoteStats オブジェクトを返す。"""
        d = self.load_stats()
        return NoteStats.from_dict(d)

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _apply_date_resets(self, stats: dict) -> dict:
        """日付が変わっていたら日次/月次カウンターをリセットする。"""
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        month_str = today.strftime("%Y-%m")

        if stats.get("last_date") != today_str:
            stats["articles_today"] = 0
            stats["last_date"] = today_str

        if stats.get("last_month") != month_str:
            stats["articles_this_month"] = 0
            stats["last_month"] = month_str

        return stats
