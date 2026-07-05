"""FortuneFactory — 占い・運勢コンテンツ生成 Factory.

設計原則:
    - AI 呼び出しは ai_task ステップへ委譲（Factory 内に AI コードなし）
    - Kernel / Router / Provider 名をハードコードしない
    - Workflow Definition を返すだけ — 実行は WorkflowRunner が行う
"""
from __future__ import annotations

from src.workflow.models import WorkflowDefinition, WorkflowStep
from src.workflow.enums import StepType, OnFailure

from .base import BaseFactory


class FortuneFactory(BaseFactory):
    """占い・運勢コンテンツ生成 Factory.

    Workflows:
        fortune.daily_fortune   — 日次運勢コンテンツ生成
        fortune.zodiac_reading  — 星座占いコンテンツ
        fortune.tarot_reading   — タロット占いコンテンツ
        fortune.lucky_advice    — ラッキーアドバイス生成
        fortune.full_package    — 全占いコンテンツのフルパッケージ
    """

    @property
    def factory_name(self) -> str:
        return "fortune"

    def build_workflow_definitions(self) -> list[WorkflowDefinition]:
        return [
            self._daily_fortune(),
            self._zodiac_reading(),
            self._tarot_reading(),
            self._lucky_advice(),
            self._full_package(),
        ]

    def get_default_context(self) -> dict:
        return {
            "date":       "",
            "zodiac":     "おひつじ座",
            "theme":      "総合運",
            "tone":       "ポジティブ・励ます",
            "target":     "20〜30代女性",
            "lucky_item": "",
        }

    # ---- Workflow Definitions ---------------------------------------

    def _daily_fortune(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="fortune.daily_fortune",
            description="日次運勢コンテンツを生成する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="fortune",
                    step_type=StepType.AI_TASK,
                    name="日次運勢生成",
                    config={
                        "task_type":  "writing",
                        "output_key": "fortune_content",
                        "prompt": (
                            "以下の条件で今日の運勢コンテンツを作成してください。\n\n"
                            "対象: {zodiac}\n"
                            "テーマ: {theme}\n"
                            "トーン: {tone}\n"
                            "ターゲット読者: {target}\n"
                            "日付: {date}\n\n"
                            "【出力形式】\n"
                            "# 今日の運勢\n\n"
                            "⭐ 総合: [星5段階]\n"
                            "💕 恋愛: [星5段階]\n"
                            "💼 仕事: [星5段階]\n"
                            "💰 金運: [星5段階]\n\n"
                            "## 今日のメッセージ\n"
                            "（200文字程度のメインメッセージ）\n\n"
                            "## ラッキーポイント\n"
                            "- ラッキーカラー:\n"
                            "- ラッキーナンバー:\n"
                            "- ラッキーアイテム:\n\n"
                            "## 今日のアドバイス\n"
                            "（具体的な行動提案）"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _zodiac_reading(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="fortune.zodiac_reading",
            description="星座占いコンテンツを生成する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="zodiac",
                    step_type=StepType.AI_TASK,
                    name="星座占い生成",
                    config={
                        "task_type":  "writing",
                        "output_key": "zodiac_content",
                        "prompt": (
                            "以下の星座について占いコンテンツを作成してください。\n\n"
                            "星座: {zodiac}\n"
                            "テーマ: {theme}\n"
                            "ターゲット: {target}\n"
                            "トーン: {tone}\n\n"
                            "【コンテンツ構成】\n"
                            "## {zodiac}の今月の運勢\n\n"
                            "### 全体運\n"
                            "（この星座の特性をふまえた詳細な運勢解説）\n\n"
                            "### 恋愛・人間関係\n\n"
                            "### 仕事・キャリア\n\n"
                            "### 健康・お金\n\n"
                            "### 今月のテーマ\n"
                            "（キーワードと行動指針）\n\n"
                            "500〜800文字で書いてください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _tarot_reading(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="fortune.tarot_reading",
            description="タロット占いコンテンツを生成する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="tarot",
                    step_type=StepType.AI_TASK,
                    name="タロット占い生成",
                    config={
                        "task_type":  "writing",
                        "output_key": "tarot_content",
                        "prompt": (
                            "タロットカードを使った占いコンテンツを作成してください。\n\n"
                            "テーマ: {theme}\n"
                            "ターゲット: {target}\n"
                            "トーン: {tone}\n\n"
                            "【コンテンツ構成】\n"
                            "## タロットが語る{theme}\n\n"
                            "### 引いたカード\n"
                            "（3枚のカードを選んで、過去・現在・未来のスプレッドで解説）\n\n"
                            "### カードのメッセージ\n"
                            "（各カードの象徴と意味）\n\n"
                            "### 総合解釈\n"
                            "（3枚のカードが伝えるメッセージ）\n\n"
                            "### あなたへのアドバイス\n"
                            "（具体的な行動提案）\n\n"
                            "神秘的でありながら希望が持てる内容にしてください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _lucky_advice(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="fortune.lucky_advice",
            description="ラッキーアドバイスとアクションプランを生成する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="lucky",
                    step_type=StepType.AI_TASK,
                    name="ラッキーアドバイス生成",
                    config={
                        "task_type":  "writing",
                        "output_key": "lucky_content",
                        "prompt": (
                            "以下の条件でラッキーアドバイスコンテンツを生成してください。\n\n"
                            "対象: {zodiac}\n"
                            "テーマ: {theme}\n"
                            "ラッキーアイテム（指定ある場合）: {lucky_item}\n"
                            "ターゲット: {target}\n\n"
                            "【出力内容】\n"
                            "## 今日のラッキーポイント\n\n"
                            "🍀 ラッキーカラー: （理由付き）\n"
                            "🔢 ラッキーナンバー: （理由付き）\n"
                            "✨ ラッキーアイテム: （使い方付き）\n"
                            "🕐 ラッキータイム: （行動提案付き）\n\n"
                            "## 運気アップの行動3選\n"
                            "1. （具体的な行動）\n"
                            "2. （具体的な行動）\n"
                            "3. （具体的な行動）\n\n"
                            "## 今日の一言\n"
                            "（短くインパクトのある励ましの言葉）"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _full_package(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="fortune.full_package",
            description="日次運勢・星座占い・ラッキーアドバイスの完全パッケージ",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="daily",
                    step_type=StepType.AI_TASK,
                    name="日次運勢",
                    config={
                        "task_type":  "writing",
                        "output_key": "daily_fortune",
                        "prompt": (
                            "{zodiac}の今日（{date}）の運勢を、{tone}なトーンで、"
                            "{target}向けに作成してください。\n"
                            "総合運・恋愛・仕事・金運の4項目と、今日のアドバイスを含めてください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="zodiac",
                    step_type=StepType.AI_TASK,
                    name="星座占い",
                    depends_on=["daily"],
                    config={
                        "task_type":  "writing",
                        "output_key": "zodiac_detail",
                        "prompt": (
                            "以下の日次運勢をふまえ、{zodiac}の詳細な星座占いを作成してください。\n\n"
                            "{daily_fortune}\n\n"
                            "今月の全体的な流れ・特別なアドバイス・注意点を加えて、"
                            "より深い占いコンテンツにしてください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="lucky",
                    step_type=StepType.AI_TASK,
                    name="ラッキーアドバイス",
                    depends_on=["zodiac"],
                    config={
                        "task_type":  "writing",
                        "output_key": "lucky_advice",
                        "prompt": (
                            "以下の占いコンテンツに合わせた、今日のラッキーアドバイスを作成してください。\n\n"
                            "{zodiac_detail}\n\n"
                            "ラッキーカラー・ナンバー・アイテム・タイムと、運気アップの行動3選を含めてください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="save_package",
                    step_type=StepType.MEMORY_UPDATE,
                    name="占いパッケージを保存",
                    depends_on=["lucky"],
                    config={
                        "key":                "last_fortune_package",
                        "value_from_context": "daily_fortune",
                        "scope":              "global",
                    },
                    on_failure=OnFailure.CONTINUE,
                ),
            ],
        )
