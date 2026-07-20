from __future__ import annotations

from pathlib import Path
from typing import Any

from src.learning_engine.business_pattern_engine import BusinessPatternEngine
from src.learning_engine.knowledge_store import LEARNING_ENGINE_PATH, KnowledgeStore
from src.learning_engine.learning_models import now_iso, require_dry_run


class BusinessPatternPipeline:
    """Generate and persist business_patterns in the local Learning Engine JSON."""

    def __init__(
        self,
        *,
        store: KnowledgeStore | None = None,
        path: str | Path = LEARNING_ENGINE_PATH,
        engine: BusinessPatternEngine | None = None,
    ) -> None:
        self.store = store or KnowledgeStore(path=path)
        self.engine = engine or BusinessPatternEngine()

    def generate_for_knowledge(self, knowledge_id: str, *, dry_run: bool = True) -> dict[str, Any]:
        require_dry_run(dry_run)
        state = self.store.load_state()
        for record in state.get("knowledge", []):
            if record.get("knowledge_id") != knowledge_id:
                continue
            pattern = self.engine.generate(record, dry_run=True)
            record["business_pattern_status"] = "generated"
            record["business_pattern_id"] = pattern["pattern_id"]
            record["business_pattern_updated_at"] = now_iso()
            self._upsert_pattern(state, pattern)
            self.store.save_state(state)
            return dict(pattern)
        return {"status": "missing", "knowledge_id": knowledge_id, "dry_run": True}

    def generate_all(self, *, dry_run: bool = True) -> list[dict[str, Any]]:
        require_dry_run(dry_run)
        state = self.store.load_state()
        patterns: list[dict[str, Any]] = []
        for record in state.get("knowledge", []):
            pattern = self.engine.generate(record, dry_run=True)
            record["business_pattern_status"] = "generated"
            record["business_pattern_id"] = pattern["pattern_id"]
            record["business_pattern_updated_at"] = now_iso()
            self._upsert_pattern(state, pattern)
            patterns.append(dict(pattern))
        self.store.save_state(state)
        return patterns

    def list_patterns(self) -> list[dict[str, Any]]:
        state = self.store.load_state()
        patterns = state.get("business_patterns", [])
        return list(patterns) if isinstance(patterns, list) else []

    @staticmethod
    def _upsert_pattern(state: dict[str, Any], pattern: dict[str, Any]) -> None:
        patterns = state.setdefault("business_patterns", [])
        source_id = pattern.get("source_knowledge_id")
        for index, existing in enumerate(patterns):
            if existing.get("source_knowledge_id") == source_id:
                pattern["pattern_id"] = existing.get("pattern_id", pattern["pattern_id"])
                patterns[index] = pattern
                break
        else:
            patterns.insert(0, pattern)
        state["business_patterns"] = patterns[:1000]
        state["business_pattern_summary"] = {
            "pattern_count": len(state["business_patterns"]),
            "updated_at": now_iso(),
        }
