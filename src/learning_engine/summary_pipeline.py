from __future__ import annotations

from pathlib import Path
from typing import Any

from src.learning_engine.knowledge_store import KnowledgeStore, LEARNING_ENGINE_PATH
from src.learning_engine.learning_models import now_iso, require_dry_run
from src.learning_engine.summary_engine import SummaryEngine


class SummaryPipeline:
    """Attach rule-based summary_data to stored knowledge records."""

    def __init__(
        self,
        *,
        store: KnowledgeStore | None = None,
        path: str | Path = LEARNING_ENGINE_PATH,
        engine: SummaryEngine | None = None,
    ) -> None:
        self.store = store or KnowledgeStore(path=path)
        self.engine = engine or SummaryEngine()

    def summarize_knowledge(self, knowledge_id: str, *, dry_run: bool = True) -> dict[str, Any]:
        require_dry_run(dry_run)
        state = self.store.load_state()
        for record in state.get("knowledge", []):
            if record.get("knowledge_id") != knowledge_id:
                continue
            summary_data = self.engine.generate(record, dry_run=True)
            record["summary_data"] = summary_data
            record["summary_status"] = "summarized"
            record["summary_updated_at"] = now_iso()
            self.store.save_state(state)
            return dict(record)
        return {"status": "missing", "knowledge_id": knowledge_id, "dry_run": True}

    def summarize_all(self, *, dry_run: bool = True) -> list[dict[str, Any]]:
        require_dry_run(dry_run)
        state = self.store.load_state()
        updated: list[dict[str, Any]] = []
        for record in state.get("knowledge", []):
            record["summary_data"] = self.engine.generate(record, dry_run=True)
            record["summary_status"] = "summarized"
            record["summary_updated_at"] = now_iso()
            updated.append(dict(record))
        self.store.save_state(state)
        return updated
