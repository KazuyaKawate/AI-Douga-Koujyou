"""NotePublisher — 記事を output/notes/{article_id}_draft.md として出力するサービス。

現在はドラフトファイルの書き出しのみ（note.com APIスタブ）。
将来は note.com API 連携で実際の投稿まで自動化する。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_OUTPUT_DIR = Path("output/notes")


@dataclass
class PublishResult:
    """NotePublisher.publish() の返り値。"""
    success:     bool
    draft_path:  str | None = None
    error:       str | None = None

    def to_dict(self) -> dict:
        return {
            "success":    self.success,
            "draft_path": self.draft_path,
            "error":      self.error,
        }


class NotePublisher:
    """
    記事コンテンツをドラフトファイルとして保存する。

    Publisher の責務:
      - output/notes/ ディレクトリの管理
      - Markdown ファイルの組み立て（フロントマター + 本文）
      - 将来の note.com API 呼び出し（スタブ）

    スタブモード: draft.md を書き出す（API呼び出しなし）
    AIモード:     将来的に note.com API 経由で投稿（未実装）
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        self._output_dir = output_dir or _OUTPUT_DIR
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def publish(
        self,
        article_id:      str,
        title:           str,
        intro:           str,
        body:            str,
        cta:             str,
        summary:         str,
        meta_description: str,
        category:        str,
        tags:            list[str],
        monetization_path: str,
    ) -> PublishResult:
        """
        記事をドラフト Markdown ファイルに書き出す。

        Returns:
            PublishResult（success=True で draft_path を含む）
        """
        try:
            md = self._build_markdown(
                article_id=article_id,
                title=title,
                intro=intro,
                body=body,
                cta=cta,
                summary=summary,
                meta_description=meta_description,
                category=category,
                tags=tags,
                monetization_path=monetization_path,
            )
            path = self._output_dir / f"{article_id}_draft.md"
            path.write_text(md, encoding="utf-8")
            return PublishResult(success=True, draft_path=str(path))
        except OSError as exc:
            return PublishResult(success=False, error=str(exc))

    def draft_exists(self, article_id: str) -> bool:
        """draft.md が存在するか確認する。"""
        return (self._output_dir / f"{article_id}_draft.md").exists()

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _build_markdown(
        self,
        article_id:      str,
        title:           str,
        intro:           str,
        body:            str,
        cta:             str,
        summary:         str,
        meta_description: str,
        category:        str,
        tags:            list[str],
        monetization_path: str,
    ) -> str:
        tag_str = ", ".join(tags)
        now = datetime.now().isoformat(timespec="seconds")
        return (
            f"---\n"
            f"article_id: {article_id}\n"
            f"title: {title}\n"
            f"category: {category}\n"
            f"tags: [{tag_str}]\n"
            f"monetization: {monetization_path}\n"
            f"summary: {summary}\n"
            f"meta_description: {meta_description}\n"
            f"created_at: {now}\n"
            f"status: draft\n"
            f"---\n\n"
            f"# {title}\n\n"
            f"{intro}\n\n"
            f"---\n\n"
            f"{body}\n\n"
            f"---\n\n"
            f"> {cta}\n"
        )
