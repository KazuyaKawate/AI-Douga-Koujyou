"""NoteFactory — BaseFactory を継承した Note記事生成Factory。

Orchestrator の FACTORY_REGISTRY に "note" として登録される。
"""
from __future__ import annotations

from pathlib import Path

from src.orchestrator.factories.base import BaseFactory

_WORKFLOW_DIR = Path("config/workflow_definitions")


class NoteFactory(BaseFactory):
    """
    note.comへの記事生成・公開を管理するFactory。

    このクラスが担う責務:
      - note_daily.json ワークフロー定義の提供
      - デフォルトコンテキストの提供
    実際の記事生成ロジックは executors.py の各 Executor に委譲する。
    """

    @property
    def factory_name(self) -> str:
        return "note"

    def build_workflow_definitions(self) -> list:
        """config/workflow_definitions/note_daily.json を読み込んで返す。"""
        from src.workflow.models import WorkflowDefinition

        path = _WORKFLOW_DIR / "note_daily.json"
        if not path.exists():
            return []
        return [WorkflowDefinition.from_file(path)]

    def get_default_context(self) -> dict:
        """Workflow 起動時に注入するデフォルトコンテキスト。"""
        return {
            "note_topic":          "",
            "note_recent_topics":  [],
            "note_article":        {},
            "note_plan":           {},
            "note_writer_output":  {},
            "note_review_result":  {},
            "note_publish_result": {},
            "note_stats":          {},
            "note_memory_saved":   False,
        }
