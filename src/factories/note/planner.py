"""NotePlanner — アイデアから記事構成計画を生成するサービス。

スタブモード: router=None のとき固定値を返す
AIモード:    router が注入されたとき AI Router 経由で生成
"""
from __future__ import annotations

from typing import Any

from src.factories.note.models import NotePlan, NoteConfig


class NotePlanner:
    """
    記事のアイデアから NotePlan（構成計画）を生成する。

    Planner の責務:
      - カテゴリ判定
      - SEOキーワード選定
      - 記事構成（アウトライン）生成
      - ターゲット読者定義
      - 収益化導線の選択
    """

    def __init__(self, router: Any | None = None, config: NoteConfig | None = None) -> None:
        self._router = router
        self._config = config or NoteConfig.load()

    def plan(self, topic: str, recent_topics: list[str] | None = None) -> NotePlan:
        """
        トピックから NotePlan を生成する。

        Args:
            topic:         記事のテーマ
            recent_topics: 重複チェック用の直近トピックリスト

        Returns:
            NotePlan
        """
        if self._router is None or self._config.stub_mode:
            return self._stub_plan(topic)
        return self._ai_plan(topic, recent_topics or [])

    # ------------------------------------------------------------------
    # スタブモード（AI Router なし・テスト用）
    # ------------------------------------------------------------------

    def _stub_plan(self, topic: str) -> NotePlan:
        return NotePlan(
            topic=topic,
            category=self._config.category_default,
            tags=["AI", "自動化", "副業"],
            target_audience="副業・自動化に興味のある会社員・フリーランス",
            seo_keywords=[topic, "AI活用", "自動化ツール"],
            monetization_path="有料記事",
            outline=[
                "## はじめに",
                "## 背景と課題",
                "## 解決策の全体像",
                "## 具体的な手順",
                "## 実際の成果・体験談",
                "## まとめと次のステップ",
            ],
            estimated_word_count=self._config.target_word_count,
        )

    # ------------------------------------------------------------------
    # AI Router モード
    # ------------------------------------------------------------------

    def _ai_plan(self, topic: str, recent_topics: list[str]) -> NotePlan:
        from src.ai.task import AITask, TaskType

        recent_str = "、".join(recent_topics) if recent_topics else "なし"
        prompt = (
            f"note.comの記事構成を考えてください。\n\n"
            f"テーマ: {topic}\n"
            f"最近書いたトピック（重複を避ける）: {recent_str}\n\n"
            f"以下のJSON形式で回答してください（JSON以外を含めないこと）:\n"
            "{\n"
            '  "category": "カテゴリ名",\n'
            '  "tags": ["タグ1", "タグ2", "タグ3"],\n'
            '  "target_audience": "ターゲット読者の説明",\n'
            '  "seo_keywords": ["キーワード1", "キーワード2", "キーワード3"],\n'
            '  "monetization_path": "有料記事 or 会員向け or 無料+CTA",\n'
            '  "outline": ["## 見出し1", "## 見出し2", "## 見出し3"],\n'
            '  "estimated_word_count": 1500\n'
            "}"
        )
        task = AITask(prompt=prompt, task_type=TaskType.DEFAULT)
        resp = self._router.complete(task)

        if not resp.ok:
            return self._stub_plan(topic)

        import json
        try:
            d = json.loads(resp.content)
            return NotePlan(
                topic=topic,
                category=d.get("category", self._config.category_default),
                tags=d.get("tags", []),
                target_audience=d.get("target_audience", ""),
                seo_keywords=d.get("seo_keywords", []),
                monetization_path=d.get("monetization_path", "有料記事"),
                outline=d.get("outline", []),
                estimated_word_count=d.get("estimated_word_count", self._config.target_word_count),
            )
        except (json.JSONDecodeError, KeyError):
            return self._stub_plan(topic)
