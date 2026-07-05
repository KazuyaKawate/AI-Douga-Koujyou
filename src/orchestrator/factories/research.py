"""ResearchFactory — リサーチ・情報収集 Factory.

設計原則:
    - AI 呼び出しは ai_task ステップへ委譲（Factory 内に AI コードなし）
    - Kernel / Router / Provider 名をハードコードしない
    - Workflow Definition を返すだけ — 実行は WorkflowRunner が行う
"""
from __future__ import annotations

from src.workflow.models import WorkflowDefinition, WorkflowStep
from src.workflow.enums import StepType, OnFailure

from .base import BaseFactory


class ResearchFactory(BaseFactory):
    """リサーチ・情報収集 Factory.

    Workflows:
        research.topic_deep_dive       — トピックを深掘り調査
        research.competitive_analysis  — 競合分析レポート
        research.market_summary        — 市場サマリ生成
        research.trend_report          — トレンドレポート
        research.full_research         — 調査→分析→レポートのフルパイプライン
    """

    @property
    def factory_name(self) -> str:
        return "research"

    def build_workflow_definitions(self) -> list[WorkflowDefinition]:
        return [
            self._topic_deep_dive(),
            self._competitive_analysis(),
            self._market_summary(),
            self._trend_report(),
            self._full_research(),
        ]

    def get_default_context(self) -> dict:
        return {
            "topic":       "",
            "industry":    "テクノロジー",
            "depth":       "詳細",
            "perspective": "ビジネス視点",
            "output_lang": "日本語",
        }

    # ---- Workflow Definitions ---------------------------------------

    def _topic_deep_dive(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="research.topic_deep_dive",
            description="トピックを多角的に深掘り調査する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="research",
                    step_type=StepType.AI_TASK,
                    name="トピック深掘り調査",
                    config={
                        "task_type":  "analysis",
                        "output_key": "research_result",
                        "prompt": (
                            "以下のトピックについて、{perspective}で詳細に調査・分析してください。\n\n"
                            "トピック: {topic}\n"
                            "業界: {industry}\n"
                            "調査深度: {depth}\n"
                            "出力言語: {output_lang}\n\n"
                            "【調査内容】\n"
                            "## 1. 概要・定義\n"
                            "（このトピックとは何か）\n\n"
                            "## 2. 現状と背景\n"
                            "（現在の状況、なぜ注目されているか）\n\n"
                            "## 3. 主要プレイヤー・事例\n"
                            "（具体的な企業・製品・実例）\n\n"
                            "## 4. 課題・リスク\n"
                            "（解決すべき問題点）\n\n"
                            "## 5. 将来展望\n"
                            "（今後の方向性と予測）\n\n"
                            "## 6. アクションアイテム\n"
                            "（ビジネスでの活用方法）"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _competitive_analysis(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="research.competitive_analysis",
            description="競合他社・競合製品を分析するレポートを生成する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="competitive",
                    step_type=StepType.AI_TASK,
                    name="競合分析",
                    config={
                        "task_type":  "analysis",
                        "output_key": "competitive_report",
                        "prompt": (
                            "以下のテーマで競合分析レポートを作成してください。\n\n"
                            "分析対象: {topic}\n"
                            "業界: {industry}\n"
                            "視点: {perspective}\n\n"
                            "【分析フレームワーク】\n"
                            "## 競合マップ\n"
                            "（主要プレイヤーの位置づけ）\n\n"
                            "## 各競合の強み・弱み\n"
                            "（3〜5社を比較）\n\n"
                            "## 差別化ポイント\n"
                            "（市場での独自価値）\n\n"
                            "## 市場シェアと成長率\n"
                            "（推定・一般情報ベース）\n\n"
                            "## 戦略的示唆\n"
                            "（どう対応すべきか）"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _market_summary(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="research.market_summary",
            description="市場概況サマリを生成する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="market",
                    step_type=StepType.AI_TASK,
                    name="市場サマリ生成",
                    config={
                        "task_type":  "analysis",
                        "output_key": "market_summary",
                        "prompt": (
                            "以下の市場について簡潔なサマリレポートを作成してください。\n\n"
                            "市場/テーマ: {topic}\n"
                            "業界セクター: {industry}\n\n"
                            "【サマリ項目】\n"
                            "- 市場規模（推定）と成長率\n"
                            "- 主要トレンド（3〜5点）\n"
                            "- 主要プレイヤー\n"
                            "- 市場の課題\n"
                            "- ビジネス機会\n"
                            "- 2〜3年後の予測\n\n"
                            "エグゼクティブサマリ形式（800文字以内）で出力してください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _trend_report(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="research.trend_report",
            description="最新トレンドレポートを生成する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="trends",
                    step_type=StepType.AI_TASK,
                    name="トレンドレポート生成",
                    config={
                        "task_type":  "analysis",
                        "output_key": "trend_report",
                        "prompt": (
                            "以下のトピックに関するトレンドレポートを作成してください。\n\n"
                            "テーマ: {topic}\n"
                            "業界: {industry}\n\n"
                            "【レポート構成】\n"
                            "# {topic} トレンドレポート\n\n"
                            "## サマリ（3行以内）\n\n"
                            "## 注目トレンド TOP5\n"
                            "1. [トレンド名]: [説明・影響]\n"
                            "...\n\n"
                            "## 先行企業の動き\n\n"
                            "## 2026年の予測\n\n"
                            "## 今すぐ取るべきアクション\n\n"
                            "具体的な数字・事例を含めてください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _full_research(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="research.full_research",
            description="深掘り調査→競合分析→レポート統合のフルパイプライン",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="deep_dive",
                    step_type=StepType.AI_TASK,
                    name="深掘り調査",
                    config={
                        "task_type":  "analysis",
                        "output_key": "deep_dive",
                        "prompt": (
                            "トピック「{topic}」について、{perspective}で深掘り調査してください。\n"
                            "業界: {industry}\n\n"
                            "概要・現状・課題・将来展望を含む詳細な調査レポートを作成してください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="competitive",
                    step_type=StepType.AI_TASK,
                    name="競合分析",
                    depends_on=["deep_dive"],
                    config={
                        "task_type":  "analysis",
                        "output_key": "competitive",
                        "prompt": (
                            "以下の調査結果をふまえ、「{topic}」の競合分析を行ってください。\n\n"
                            "{deep_dive}\n\n"
                            "主要プレイヤーの比較・差別化・戦略的示唆を含めてください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="final_report",
                    step_type=StepType.AI_TASK,
                    name="最終レポート統合",
                    depends_on=["competitive"],
                    config={
                        "task_type":  "writing",
                        "output_key": "final_report",
                        "prompt": (
                            "以下の調査と競合分析を統合した、意思決定に使えるエグゼクティブレポートを作成してください。\n\n"
                            "【深掘り調査】\n{deep_dive}\n\n"
                            "【競合分析】\n{competitive}\n\n"
                            "マネジメント向けに要点を絞り、「なぜ重要か」「何をすべきか」を明確にしてください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="save_report",
                    step_type=StepType.MEMORY_UPDATE,
                    name="レポートを保存",
                    depends_on=["final_report"],
                    config={
                        "key":                "last_research_report",
                        "value_from_context": "final_report",
                        "scope":              "global",
                    },
                    on_failure=OnFailure.CONTINUE,
                ),
            ],
        )
