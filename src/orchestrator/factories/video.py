"""VideoFactory — 動画コンテンツ生成 Factory.

設計原則:
    - AI 呼び出しは ai_task ステップへ委譲（Factory 内に AI コードなし）
    - Kernel / Router / Provider 名をハードコードしない
    - Workflow Definition を返すだけ — 実行は WorkflowRunner が行う
"""
from __future__ import annotations

from src.workflow.models import WorkflowDefinition, WorkflowStep
from src.workflow.enums import StepType, OnFailure

from .base import BaseFactory


class VideoFactory(BaseFactory):
    """動画コンテンツ生成 Factory.

    Workflows:
        video.script_generate  — トピックから動画台本を生成
        video.scene_breakdown  — 台本をシーン別に分割
        video.image_prompts    — 各シーンの画像生成プロンプトを作成
        video.full_production  — 台本→シーン→画像プロンプトのフルパイプライン
    """

    @property
    def factory_name(self) -> str:
        return "video"

    def build_workflow_definitions(self) -> list[WorkflowDefinition]:
        return [
            self._script_generate(),
            self._scene_breakdown(),
            self._image_prompts(),
            self._full_production(),
        ]

    def get_default_context(self) -> dict:
        return {
            "topic":        "",
            "duration_sec": "60",
            "style":        "ナレーション動画",
            "target":       "一般視聴者",
            "language":     "日本語",
        }

    # ---- Workflow Definitions ---------------------------------------

    def _script_generate(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="video.script_generate",
            description="トピックから動画台本を AI 生成する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="script",
                    step_type=StepType.AI_TASK,
                    name="動画台本生成",
                    config={
                        "task_type":  "writing",
                        "output_key": "script",
                        "prompt": (
                            "以下の条件で動画用の台本を作成してください。\n\n"
                            "テーマ: {topic}\n"
                            "動画尺: 約{duration_sec}秒\n"
                            "スタイル: {style}\n"
                            "ターゲット: {target}\n"
                            "言語: {language}\n\n"
                            "【出力形式】\n"
                            "# タイトル\n\n"
                            "## オープニング（約10秒）\n"
                            "（視聴者を引き込むフック）\n\n"
                            "## メインコンテンツ（約40秒）\n"
                            "（3〜5つのポイントを簡潔に）\n\n"
                            "## クロージング（約10秒）\n"
                            "（まとめ + 行動喚起）\n\n"
                            "各セクションにナレーションテキストを含めてください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _scene_breakdown(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="video.scene_breakdown",
            description="台本をシーン別に分割・詳細化する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="scenes",
                    step_type=StepType.AI_TASK,
                    name="シーン分割",
                    config={
                        "task_type":  "planning",
                        "output_key": "scenes",
                        "prompt": (
                            "以下の動画台本をシーン別に分割してください。\n\n"
                            "{script}\n\n"
                            "【出力形式 (JSON)】\n"
                            "```json\n"
                            "[\n"
                            '  {\n'
                            '    "scene_id": 1,\n'
                            '    "duration_sec": 10,\n'
                            '    "narration": "ナレーションテキスト",\n'
                            '    "visual": "映像の説明",\n'
                            '    "bgm": "BGMの雰囲気"\n'
                            '  }\n'
                            "]\n"
                            "```\n"
                            "JSON のみ出力してください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _image_prompts(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="video.image_prompts",
            description="シーンリストから画像生成プロンプトを作成する",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="image_prompts",
                    step_type=StepType.AI_TASK,
                    name="画像プロンプト生成",
                    config={
                        "task_type":  "writing",
                        "output_key": "image_prompts",
                        "prompt": (
                            "以下のシーン情報から、各シーン用の画像生成プロンプトを作成してください。\n\n"
                            "シーン情報:\n{scenes}\n\n"
                            "【ルール】\n"
                            "- 各プロンプトは英語で記述\n"
                            "- 具体的な視覚描写を含める\n"
                            "- スタイル指定を末尾に追加（例: cinematic, 4k, professional）\n\n"
                            "【出力形式 (JSON)】\n"
                            "```json\n"
                            "[\n"
                            '  {\n'
                            '    "scene_id": 1,\n'
                            '    "prompt": "English prompt here, cinematic, 4k",\n'
                            '    "negative_prompt": "blurry, low quality"\n'
                            '  }\n'
                            "]\n"
                            "```"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
            ],
        )

    def _full_production(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="video.full_production",
            description="台本生成→シーン分割→画像プロンプト生成のフルパイプライン",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="script",
                    step_type=StepType.AI_TASK,
                    name="台本生成",
                    config={
                        "task_type":  "writing",
                        "output_key": "script",
                        "prompt": (
                            "以下の条件で動画台本を作成してください。\n\n"
                            "テーマ: {topic}\n"
                            "動画尺: 約{duration_sec}秒\n"
                            "スタイル: {style}\n"
                            "ターゲット: {target}\n\n"
                            "オープニング・メインコンテンツ・クロージングの構成で、"
                            "ナレーションテキストを含む台本を書いてください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="scenes",
                    step_type=StepType.AI_TASK,
                    name="シーン分割",
                    depends_on=["script"],
                    config={
                        "task_type":  "planning",
                        "output_key": "scenes",
                        "prompt": (
                            "以下の台本を3〜6のシーンに分割し、各シーンのナレーションと映像描写をまとめてください。\n\n"
                            "{script}\n\n"
                            "シーン番号・推定秒数・ナレーション・映像説明の形式で出力してください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="image_prompts",
                    step_type=StepType.AI_TASK,
                    name="画像プロンプト生成",
                    depends_on=["scenes"],
                    config={
                        "task_type":  "writing",
                        "output_key": "image_prompts",
                        "prompt": (
                            "以下のシーン情報をもとに、各シーン用の英語画像生成プロンプトを作成してください。\n\n"
                            "{scenes}\n\n"
                            "各シーンに対して: scene番号、英語プロンプト（cinematic, 4k スタイル付き）を出力してください。"
                        ),
                    },
                    retry_max=1,
                    on_failure=OnFailure.ABORT,
                ),
                WorkflowStep(
                    step_id="save_result",
                    step_type=StepType.MEMORY_UPDATE,
                    name="生成結果を保存",
                    depends_on=["image_prompts"],
                    config={
                        "key":                "last_video_production",
                        "value_from_context": "script",
                        "scope":              "global",
                    },
                    on_failure=OnFailure.CONTINUE,
                ),
            ],
        )
