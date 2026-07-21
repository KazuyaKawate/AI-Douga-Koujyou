from __future__ import annotations

from pathlib import Path
from typing import Any

from src.learning_engine.knowledge_store import LEARNING_ENGINE_PATH, KnowledgeStore
from src.learning_engine.learning_models import require_dry_run


class CommanderTaskImporter:
    """Read pending Commander learning tasks without modifying Commander state."""

    def __init__(self, *, store: KnowledgeStore | None = None, path: str | Path = LEARNING_ENGINE_PATH) -> None:
        self.store = store or KnowledgeStore(path=path)

    def load_pending_tasks(self, *, limit: int | None = None, dry_run: bool = True) -> list[dict[str, Any]]:
        require_dry_run(dry_run)
        state = self.store.load_state()
        tasks = state.get("commander_learning_tasks", [])
        if not isinstance(tasks, list):
            return []
        pending = [dict(task) for task in tasks if task.get("status", "pending") == "pending"]
        ordered = sorted(
            pending,
            key=lambda task: (
                -self._priority_weight(str(task.get("priority", "LOW"))),
                self._int_value(task, "estimated_profit_days", 9999),
                self._int_value(task, "estimated_initial_cost", 999999),
                -self._int_value(task, "confidence", 0),
            ),
        )
        return ordered if limit is None else ordered[: max(0, int(limit))]

    @staticmethod
    def _priority_weight(priority: str) -> int:
        normalized = priority.strip().upper()
        return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(normalized, 0)

    @staticmethod
    def _int_value(row: dict[str, Any], key: str, default: int) -> int:
        try:
            return int(row.get(key, default))
        except (TypeError, ValueError):
            return default
