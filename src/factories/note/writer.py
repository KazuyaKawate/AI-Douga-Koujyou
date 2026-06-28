"""NoteWriter — NotePlan から記事本文を生成するサービス。

スタブモード: router=None のとき固定値を返す
AIモード:    router が注入されたとき AI Router 経由で生成

生成物:
  title           記事タイトル（SEOを意識）
  intro           導入文（読者の課題・共感から始める）
  body            本文（アウトラインに沿った全文）
  cta             Call To Action（有料記事への導線 or フォロー依頼）
  summary         要約（100文字以内、SNSシェア用）
  meta_description メタディスクリプション（SEO用、120文字以内）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.factories.note.models import NoteConfig, NotePlan


@dataclass
class WriterOutput:
    """NoteWriter の返り値。"""
    title:            str
    intro:            str
    body:             str
    cta:              str
    summary:          str
    meta_description: str
    word_count:       int

    def to_dict(self) -> dict:
        return {
            "title":            self.title,
            "intro":            self.intro,
            "body":             self.body,
            "cta":              self.cta,
            "summary":          self.summary,
            "meta_description": self.meta_description,
            "word_count":       self.word_count,
        }


class NoteWriter:
    """
    NotePlan から記事コンテンツを生成する。

    Writer の責務:
      - タイトル生成
      - 導入文生成（共感・課題提示）
      - 本文生成（アウトライン展開）
      - CTA生成（収益化に合わせた訴求）
      - 要約・メタディスクリプション生成
    """

    def __init__(self, router: Any | None = None, config: NoteConfig | None = None) -> None:
        self._router = router
        self._config = config or NoteConfig.load()

    def write(self, plan: NotePlan) -> WriterOutput:
        """
        NotePlan から記事コンテンツを生成する。

        Args:
            plan: NotePlanner が生成した構成計画

        Returns:
            WriterOutput
        """
        if self._router is None or self._config.stub_mode:
            return self._stub_write(plan)
        return self._ai_write(plan)

    # ------------------------------------------------------------------
    # スタブモード
    # ------------------------------------------------------------------

    def _stub_write(self, plan: NotePlan) -> WriterOutput:
        outline_text = "\n\n".join(
            f"{h}\nここに{h.lstrip('#').strip()}の内容が入ります。"
            f"ターゲット読者（{plan.target_audience}）に向けた具体的な説明を記述します。"
            for h in plan.outline
        )
        body = f"# {plan.topic}\n\n{outline_text}"
        word_count = len(body.replace("\n", "").replace(" ", ""))

        cta = (
            "この記事が役に立ったらスキ・フォローをお願いします！"
            if plan.monetization_path == "無料+CTA"
            else f"続きは有料パートで詳しく解説しています（{self._config.price_jpy}円）。"
        )

        return WriterOutput(
            title=f"【保存版】{plan.topic}を徹底解説",
            intro=(
                f"「{plan.topic}について知りたい」と思っているあなたへ。\n"
                f"この記事では{plan.target_audience}に向けて、"
                f"{plan.topic}の基本から実践まで解説します。"
            ),
            body=body,
            cta=cta,
            summary=f"{plan.topic}を{plan.target_audience}向けにわかりやすく解説した記事です。",
            meta_description=f"{plan.topic}について解説。"
                             f"キーワード：{'、'.join(plan.seo_keywords[:3])}",
            word_count=word_count,
        )

    # ------------------------------------------------------------------
    # AI Router モード
    # ------------------------------------------------------------------

    def _ai_write(self, plan: NotePlan) -> WriterOutput:
        from src.ai.task import AITask, TaskType
        import json

        outline_str = "\n".join(plan.outline)
        prompt = (
            f"以下の構成でnote記事を書いてください。\n\n"
            f"テーマ: {plan.topic}\n"
            f"ターゲット読者: {plan.target_audience}\n"
            f"SEOキーワード: {', '.join(plan.seo_keywords)}\n"
            f"収益化導線: {plan.monetization_path}\n"
            f"目標文字数: {plan.estimated_word_count}文字\n"
            f"アウトライン:\n{outline_str}\n\n"
            "以下のJSON形式で回答してください（JSON以外を含めないこと）:\n"
            "{\n"
            '  "title": "記事タイトル",\n'
            '  "intro": "導入文（200字程度）",\n'
            '  "body": "本文（アウトライン全展開）",\n'
            '  "cta": "CTA文（50字程度）",\n'
            '  "summary": "要約（100字以内）",\n'
            '  "meta_description": "メタディスクリプション（120字以内）"\n'
            "}"
        )

        task = AITask(prompt=prompt, task_type=TaskType.DEFAULT)
        resp = self._router.complete(task)

        if not resp.ok:
            return self._stub_write(plan)

        try:
            d = json.loads(resp.content)
            body = d.get("body", "")
            word_count = len(body.replace("\n", "").replace(" ", ""))
            return WriterOutput(
                title=d.get("title", f"{plan.topic}について"),
                intro=d.get("intro", ""),
                body=body,
                cta=d.get("cta", ""),
                summary=d.get("summary", ""),
                meta_description=d.get("meta_description", ""),
                word_count=word_count,
            )
        except (json.JSONDecodeError, KeyError):
            return self._stub_write(plan)
