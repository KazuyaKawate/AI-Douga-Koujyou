from __future__ import annotations

from pathlib import Path
from typing import Any

from src.commander.task_generator import CommanderTaskGenerator
from src.learning_engine.knowledge_store import LEARNING_ENGINE_PATH, KnowledgeStore
from src.learning_engine.learning_models import now_iso, require_dry_run


class CommanderLearningBridge:
    """Read Learning Engine candidate rankings and save Commander task suggestions."""

    def __init__(
        self,
        *,
        store: KnowledgeStore | None = None,
        path: str | Path = LEARNING_ENGINE_PATH,
        generator: CommanderTaskGenerator | None = None,
    ) -> None:
        self.store = store or KnowledgeStore(path=path)
        self.generator = generator or CommanderTaskGenerator()

    def load_top_rankings(self, *, limit: int = 10) -> list[dict[str, Any]]:
        state = self.store.load_state()
        rankings = state.get("candidate_rankings", [])
        if not isinstance(rankings, list):
            return []
        return list(rankings)[: max(0, limit)]

    def generate_tasks(self, *, limit: int = 10, dry_run: bool = True) -> list[dict[str, Any]]:
        require_dry_run(dry_run)
        state = self.store.load_state()
        rankings = state.get("candidate_rankings", [])
        patterns = state.get("business_patterns", [])
        if not isinstance(rankings, list):
            rankings = []
        if not isinstance(patterns, list):
            patterns = []
        tasks = self.generator.generate_tasks(rankings, patterns=patterns, limit=limit, dry_run=True)
        state["commander_learning_tasks"] = tasks
        state["commander_learning_summary"] = {
            "source": "learning_engine.candidate_rankings",
            "input_count": len(rankings),
            "task_count": len(tasks),
            "top_task_id": tasks[0]["task_id"] if tasks else "",
            "status": "pending",
            "review_required": True,
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "updated_at": now_iso(),
        }
        self.store.save_state(state)
        return tasks
