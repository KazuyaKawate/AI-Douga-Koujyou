"""WritingFactory — 文章・記事生成 Factory.

設計原則:
    - AI 呼び出しは ai_task ステップへ委譲（Factory 内に AI コードなし）
    - Kernel / Router / Provider 名をハードコードしない
    - Workflow Definition を返すだけ — 実行は WorkflowRunner が行う
    - 100 個の Factory が増えてもこのファイルの設計は変わらない
"""
from __future__ import annotations

from src.workflow.models import WorkflowDefinition, WorkflowStep
from src.workflow.enums import StepType, OnFailure

from .base import BaseFactory


class WritingFactory(BaseFactory):
    """文章・記事生成 Factory."""

    @property
    def factory_name(self) -> str:
        return "writing"

    def build_workflow_definitions(self) -> list[WorkflowDefinition]:
        return [
            self._article_draft(),
            self._article_polish(),
            self._article_full(),
            self._seo_meta(),
        ]

    def get_default_context(self) -> dict:
        return {
            "topic":       "",
            "tone":        "分かりやすく実践的",
            "word_count":  "1500",
            "target":      "一般読者",
            "article_url": "",
        }

    # ---- Workflow Definitions ----------------------------------------

    def _article_draft(self) -> WorkflowDefinition:
        """Step 1: トピックから記事ドラフトを生成する。"""
        return WorkflowDefinition(
            name="writing.article_draft",
            description="トピックから記事ドラフトを AI 生成する（1ステップ）",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="draft",
                    step_type=StepType.AI_TASK,
                    name="記事ドラフト生成",
                    config={
                        "task_type":  "writing",
                        "output_key": "draft",
                        "prompt": (
                            "以下のトピックについて日本語で記事を書いてください。\n\n"
                            "トピック: {topic}\n"
                            "文字数の目安: {word_count}文字\n"
                            "トーン: {tone}\n"
                            "対象読者: {target}\n\n"
                            "【構成】\n"
                            "# タイトル（キャッチーで検索されやすいもの）\n\n"
                            "## はじめに（読者の悩みに共感する導入）\n\n"
                            "## 本文（3〜5つの見出しで構成）\n\n"
                            "## まとめ（読者へのアクションを促す締め）\n\n"
                            "マークダウン形式で記述してください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _article_polish(self) -> WorkflowDefinition:
        """Step 1: 既存ドラフトをリライト・ブラッシュアップする。"""
        return WorkflowDefinition(
            name="writing.article_polish",
            description="既存ドラフトをブラッシュアップする（1ステップ）",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="polish",
                    step_type=StepType.AI_TASK,
                    name="記事リライト",
                    config={
                        "task_type":  "writing",
                        "output_key": "polished",
                        "prompt": (
                            "以下の記事をリライトしてください。\n\n"
                            "{draft}\n\n"
                            "【改善ポイント】\n"
                            "- 読みやすさを向上させる\n"
                            "- 見出しをより魅力的にする\n"
                            "- 具体例・数字を追加する\n"
                            "- 接続詞を整理して文章の流れを改善する\n"
                            "- 結論をより明確にする\n\n"
                            "マークダウン形式で出力してください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _article_full(self) -> WorkflowDefinition:
        """Step 1→2→3: ドラフト → ポリッシュ → Memory保存 の完全パイプライン。"""
        return WorkflowDefinition(
            name="writing.article_full",
            description="トピックから完成記事まで自動生成するフルパイプライン",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="draft",
                    step_type=StepType.AI_TASK,
                    name="ドラフト生成",
                    config={
                        "task_type":  "writing",
                        "output_key": "draft",
                        "prompt": (
                            "以下のトピックについて日本語で記事のドラフトを書いてください。\n\n"
                            "トピック: {topic}\n"
                            "文字数の目安: {word_count}文字\n"
                            "トーン: {tone}\n"
                            "対象読者: {target}\n\n"
                            "マークダウン形式で記述してください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="polish",
                    step_type=StepType.AI_TASK,
                    name="ブラッシュアップ",
                    depends_on=["draft"],
                    config={
                        "task_type":  "writing",
                        "output_key": "article",
                        "prompt": (
                            "以下の記事ドラフトをブラッシュアップしてください。\n\n"
                            "{draft}\n\n"
                            "【改善ポイント】\n"
                            "- 読みやすさ・流れの改善\n"
                            "- 見出しの魅力向上\n"
                            "- 具体例・数字の追加\n"
                            "- 結論の明確化\n\n"
                            "マークダウン形式で最終版を出力してください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="save_memory",
                    step_type=StepType.MEMORY_UPDATE,
                    name="Memory 保存",
                    depends_on=["polish"],
                    config={
                        "key":                "last_article",
                        "value_from_context": "article",
                        "scope":              "global",
                    },
                    on_failure=OnFailure.CONTINUE,
                ),
            ],
        )

    def _seo_meta(self) -> WorkflowDefinition:
        """既存記事から SEO メタデータ（タイトル・ディスクリプション・タグ）を生成する。"""
        return WorkflowDefinition(
            name="writing.seo_meta",
            description="記事から SEO メタデータを生成する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="seo",
                    step_type=StepType.AI_TASK,
                    name="SEOメタ生成",
                    config={
                        "task_type":  "writing",
                        "output_key": "seo_meta",
                        "prompt": (
                            "以下の記事に対して SEO 最適化されたメタデータを生成してください。\n\n"
                            "{article}\n\n"
                            "【出力形式（JSON）】\n"
                            "```json\n"
                            "{\n"
                            '  "title": "（60文字以内の SEO タイトル）",\n'
                            '  "description": "（120〜160文字のメタディスクリプション）",\n'
                            '  "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"],\n'
                            '  "slug": "url-friendly-slug"\n'
                            "}\n"
                            "```\n"
                            "JSON のみ出力してください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )
