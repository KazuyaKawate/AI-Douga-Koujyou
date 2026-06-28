"""Note Factory Executor群 — 7種のステップ実装。

各 Executor は BaseFactoryExecutor を継承し、
EXECUTOR_REGISTRY に登録される（__init__.py で実施）。

WorkflowRunner から呼ばれる流れ:
  runner._build_executor(step) → EXECUTOR_REGISTRY["note_idea"] → NoteIdeaExecutor
  executor.execute(step, status) → _execute() → status.context へ書き込み → StepResult
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.factories.framework.executor import BaseFactoryExecutor
from src.workflow.executors.base import StepResult
from src.factories.note.models import (
    ArticleStatus, NoteArticle, NoteConfig, NotePlan,
)
from src.factories.note.planner import NotePlanner
from src.factories.note.writer import NoteWriter
from src.factories.note.publisher import NotePublisher
from src.factories.note.memory import NoteMemory
from src.factories.note.analyzer import NoteAnalyzer

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


# ---------------------------------------------------------------------------
# 1. NoteIdeaExecutor — トピックを決定し article を初期化
# ---------------------------------------------------------------------------

class NoteIdeaExecutor(BaseFactoryExecutor):
    """
    アイデア生成ステップ。

    context 書き込み:
      note_article_id  : str  — 新規記事ID
      note_topic       : str  — 決定したトピック
      note_recent_topics: list[str] — 直近トピック（Plannerへ引き継ぎ）

    step.config キー:
      topic : str — 固定トピックを指定する場合（省略可）
    """

    @property
    def step_type(self) -> str:
        return "note_idea"

    def _execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        config = NoteConfig.load()
        memory = NoteMemory()
        recent_topics = memory.get_recent_topics(10)

        topic = (
            step.config.get("topic")
            or status.context.get("note_topic")
            or self._generate_topic(recent_topics, config)
        )

        article = NoteArticle.new(topic)
        status.context["note_article_id"]    = article.article_id
        status.context["note_topic"]         = article.topic
        status.context["note_recent_topics"] = recent_topics
        status.context["note_article"]       = article.to_dict()

        return StepResult(
            success=True,
            output={"article_id": article.article_id, "topic": topic},
        )

    def _generate_topic(self, recent_topics: list[str], config: NoteConfig) -> str:
        if not self.has_router or config.stub_mode:
            return "AIを使って副業収入を自動化する方法"
        try:
            from src.ai.task import AITask, TaskType
            recent_str = "、".join(recent_topics) if recent_topics else "なし"
            prompt = (
                f"note.comで読まれやすい日本語記事のテーマを1つ提案してください。\n"
                f"最近書いたテーマ（重複を避ける）: {recent_str}\n"
                f"テーマだけを1行で返してください（説明不要）。"
            )
            resp = self._router.complete(AITask(prompt=prompt, task_type=TaskType.DEFAULT))
            if resp.ok:
                return resp.content.strip().split("\n")[0]
        except Exception:
            pass
        return "AIを使って副業収入を自動化する方法"


# ---------------------------------------------------------------------------
# 2. NotePlanExecutor — 構成計画を生成
# ---------------------------------------------------------------------------

class NotePlanExecutor(BaseFactoryExecutor):
    """
    構成計画生成ステップ。

    context 読み取り: note_topic, note_recent_topics
    context 書き込み: note_plan (NotePlan.to_dict())
    """

    @property
    def step_type(self) -> str:
        return "note_plan"

    def _execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        topic = status.context.get("note_topic", "")
        if not topic:
            return StepResult(success=False, error="note_topic が context にありません")

        recent_topics = status.context.get("note_recent_topics", [])
        planner = NotePlanner(router=self._router)
        plan = planner.plan(topic, recent_topics)

        status.context["note_plan"] = plan.to_dict()
        article_dict = status.context.get("note_article", {})
        article_dict["status"] = ArticleStatus.PLANNED.value
        article_dict["plan"]   = plan.to_dict()
        status.context["note_article"] = article_dict

        return StepResult(success=True, output=plan.to_dict())


# ---------------------------------------------------------------------------
# 3. NoteWriteExecutor — 本文を執筆
# ---------------------------------------------------------------------------

class NoteWriteExecutor(BaseFactoryExecutor):
    """
    執筆ステップ。

    context 読み取り: note_plan
    context 書き込み: note_writer_output (WriterOutput.to_dict())
    """

    @property
    def step_type(self) -> str:
        return "note_write"

    def _execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        plan_dict = status.context.get("note_plan")
        if not plan_dict:
            return StepResult(success=False, error="note_plan が context にありません")

        plan = NotePlan.from_dict(plan_dict)
        writer = NoteWriter(router=self._router)
        out = writer.write(plan)

        status.context["note_writer_output"] = out.to_dict()
        article_dict = status.context.get("note_article", {})
        article_dict.update({
            "status":           ArticleStatus.DRAFT.value,
            "title":            out.title,
            "intro":            out.intro,
            "body":             out.body,
            "cta":              out.cta,
            "summary":          out.summary,
            "meta_description": out.meta_description,
            "word_count":       out.word_count,
        })
        status.context["note_article"] = article_dict

        return StepResult(success=True, output=out.to_dict())


# ---------------------------------------------------------------------------
# 4. NoteReviewExecutor — 品質レビュー
# ---------------------------------------------------------------------------

class NoteReviewExecutor(BaseFactoryExecutor):
    """
    品質レビューステップ。

    チェック項目: 文字数/禁止語/構成/CTA有無
    context 読み取り: note_writer_output, note_plan
    context 書き込み: note_review_result {passed, notes, word_count}
    """

    @property
    def step_type(self) -> str:
        return "note_review"

    def _execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        config = NoteConfig.load()
        writer_out = status.context.get("note_writer_output", {})
        body  = writer_out.get("body", "")
        title = writer_out.get("title", "")
        cta   = writer_out.get("cta", "")
        word_count = writer_out.get("word_count", 0)

        notes: list[str] = []

        # 文字数チェック
        if word_count < config.min_word_count:
            notes.append(f"文字数不足: {word_count}字（最低{config.min_word_count}字）")
        if word_count > config.max_word_count:
            notes.append(f"文字数超過: {word_count}字（上限{config.max_word_count}字）")

        # 禁止語チェック
        for word in config.forbidden_words:
            if word in body or word in title:
                notes.append(f"禁止語を含む: 「{word}」")

        # 必須要素チェック
        if not title:
            notes.append("タイトルが空です")
        if not cta:
            notes.append("CTAが空です")
        if not body:
            notes.append("本文が空です")

        passed = len(notes) == 0
        review_result = {"passed": passed, "notes": notes, "word_count": word_count}
        status.context["note_review_result"] = review_result

        article_dict = status.context.get("note_article", {})
        article_dict["status"]       = ArticleStatus.REVIEWED.value
        article_dict["review_notes"] = notes
        status.context["note_article"] = article_dict

        if not passed:
            # on_failure=skip で次へ進む設定を想定（Workflow側で制御）
            return StepResult(
                success=False,
                error=f"レビュー失敗: {'; '.join(notes)}",
                output=review_result,
            )

        return StepResult(success=True, output=review_result)


# ---------------------------------------------------------------------------
# 5. NotePublishExecutor — ドラフトファイル出力
# ---------------------------------------------------------------------------

class NotePublishExecutor(BaseFactoryExecutor):
    """
    公開（ドラフト出力）ステップ。

    context 読み取り: note_article, note_plan, note_writer_output
    context 書き込み: note_publish_result {success, draft_path}
    """

    @property
    def step_type(self) -> str:
        return "note_publish"

    def _execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        article_dict = status.context.get("note_article", {})
        plan_dict    = status.context.get("note_plan", {})
        writer_out   = status.context.get("note_writer_output", {})

        article_id       = article_dict.get("article_id", "unknown")
        title            = writer_out.get("title", article_dict.get("title", ""))
        intro            = writer_out.get("intro", article_dict.get("intro", ""))
        body             = writer_out.get("body", article_dict.get("body", ""))
        cta              = writer_out.get("cta", article_dict.get("cta", ""))
        summary          = writer_out.get("summary", article_dict.get("summary", ""))
        meta_description = writer_out.get("meta_description", article_dict.get("meta_description", ""))
        category         = plan_dict.get("category", "テクノロジー")
        tags             = plan_dict.get("tags", [])
        monetization     = plan_dict.get("monetization_path", "無料+CTA")

        publisher = NotePublisher()
        result = publisher.publish(
            article_id=article_id,
            title=title,
            intro=intro,
            body=body,
            cta=cta,
            summary=summary,
            meta_description=meta_description,
            category=category,
            tags=tags,
            monetization_path=monetization,
        )

        if not result.success:
            return StepResult(success=False, error=result.error)

        article_dict["status"]     = ArticleStatus.PUBLISHED.value
        article_dict["draft_path"] = result.draft_path
        article_dict["word_count"] = writer_out.get("word_count", 0)
        status.context["note_article"]        = article_dict
        status.context["note_publish_result"] = result.to_dict()

        return StepResult(
            success=True,
            output={
                "draft_path":       result.draft_path,
                "word_count":       article_dict["word_count"],
                "monetization_path": monetization,
            },
        )


# ---------------------------------------------------------------------------
# 6. NoteAnalyzeExecutor — 統計更新
# ---------------------------------------------------------------------------

class NoteAnalyzeExecutor(BaseFactoryExecutor):
    """
    統計更新ステップ。

    context 読み取り: note_publish_result, note_plan
    context 書き込み: note_stats (NoteStats.to_dict())
    """

    @property
    def step_type(self) -> str:
        return "note_analyze"

    def _execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        config = NoteConfig.load()
        publish_result = status.context.get("note_publish_result", {})
        plan_dict      = status.context.get("note_plan", {})
        article_dict   = status.context.get("note_article", {})

        analyzer = NoteAnalyzer(price_jpy=config.price_jpy)
        stats = analyzer.update_stats({
            "article_id":        article_dict.get("article_id", ""),
            "word_count":        publish_result.get("word_count", 0),
            "monetization_path": plan_dict.get("monetization_path", "無料+CTA"),
        })

        article_dict["status"] = ArticleStatus.ANALYZED.value
        status.context["note_article"] = article_dict
        status.context["note_stats"]   = stats

        return StepResult(success=True, output=stats)


# ---------------------------------------------------------------------------
# 7. NoteMemoryExecutor — 記事履歴を永続化
# ---------------------------------------------------------------------------

class NoteMemoryExecutor(BaseFactoryExecutor):
    """
    メモリ保存ステップ。

    context 読み取り: note_article, note_plan
    context 書き込み: note_memory_saved (bool)
    """

    @property
    def step_type(self) -> str:
        return "note_memory"

    def _execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        article_dict = status.context.get("note_article", {})
        plan_dict    = status.context.get("note_plan", {})

        memory = NoteMemory()
        memory.add_article(
            article_id=article_dict.get("article_id", ""),
            topic=article_dict.get("topic", ""),
            title=article_dict.get("title", ""),
            category=plan_dict.get("category", ""),
            word_count=article_dict.get("word_count", 0),
            status=article_dict.get("status", ""),
            draft_path=article_dict.get("draft_path"),
        )

        status.context["note_memory_saved"] = True

        return StepResult(
            success=True,
            output={"saved": True, "article_id": article_dict.get("article_id", "")},
        )
