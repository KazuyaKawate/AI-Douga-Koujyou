"""NoteMemory — 記事の執筆履歴を JSON で永続化する。

data/note_memory.json に記事サマリーを蓄積し、
Workflow の note_memory ステップから呼ばれる。

将来の Writing/Video Factory も同様に BaseFactoryMemory を継承する。
"""
from __future__ import annotations

from pathlib import Path

from src.factories.framework.memory import BaseFactoryMemory

_DEFAULT_PATH = Path("data/note_memory.json")


class NoteMemory(BaseFactoryMemory):
    """
    Note Factory 専用 Memory。

    各エントリのスキーマ:
    {
      "article_id":  str,
      "topic":       str,
      "title":       str,
      "category":    str,
      "word_count":  int,
      "status":      str,
      "draft_path":  str | None,
      "created_at":  str (ISO8601)
    }
    """

    def __init__(self, path: Path | None = None) -> None:
        super().__init__(path or _DEFAULT_PATH)

    def add_article(
        self,
        article_id:  str,
        topic:       str,
        title:       str,
        category:    str,
        word_count:  int,
        status:      str,
        draft_path:  str | None = None,
    ) -> None:
        """記事1件をメモリに追加する。"""
        self.add_entry({
            "article_id": article_id,
            "topic":      topic,
            "title":      title,
            "category":   category,
            "word_count": word_count,
            "status":     status,
            "draft_path": draft_path,
        })

    def get_recent_topics(self, n: int = 5) -> list[str]:
        """直近 n 件のトピックリストを返す（重複ネタ防止用）。"""
        return [e.get("topic", "") for e in self.get_recent(n)]
