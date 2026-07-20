from __future__ import annotations

from pathlib import Path
from typing import Any

from src.learning_engine.learning_models import KnowledgeRecord, now_iso, require_dry_run
from src.learning_engine.source_registry import SourceRegistry
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


LEARNING_ENGINE_PATH = PROJECT_ROOT / "config" / "learning_engine.json"
LEARNING_STORE_PATH = PROJECT_ROOT / "config" / "learning_store.json"


def default_learning_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "dry_run": True,
        "local_first": True,
        "external_api_enabled": False,
        "production_actions_enabled": False,
        "sources": SourceRegistry().list_sources(),
        "knowledge": [],
        "business_patterns": [],
        "business_pattern_summary": {
            "pattern_count": 0,
        },
        "candidate_rankings": [],
        "candidate_ranking_summary": {
            "candidate_count": 0,
            "ranking_count": 0,
        },
        "commander_learning_tasks": [],
        "commander_learning_summary": {
            "task_count": 0,
            "status": "pending",
        },
        "summary": {
            "source_count": 6,
            "knowledge_count": 0,
            "status_counts": {},
        },
        "updated_at": now_iso(),
    }


class KnowledgeStore:
    def __init__(self, path: str | Path = LEARNING_ENGINE_PATH) -> None:
        self.path = Path(path)

    def load_state(self) -> dict[str, Any]:
        data = load_json(self.path, default=None)
        if not isinstance(data, dict):
            data = default_learning_state()
        defaults = default_learning_state()
        for key, value in defaults.items():
            data.setdefault(key, value)
        data["dry_run"] = True
        data["local_first"] = True
        data["external_api_enabled"] = False
        data["production_actions_enabled"] = False
        if not isinstance(data.get("sources"), list):
            data["sources"] = defaults["sources"]
        if not isinstance(data.get("knowledge"), list):
            data["knowledge"] = []
        if not isinstance(data.get("business_patterns"), list):
            data["business_patterns"] = []
        if not isinstance(data.get("business_pattern_summary"), dict):
            data["business_pattern_summary"] = {"pattern_count": len(data["business_patterns"])}
        if not isinstance(data.get("candidate_rankings"), list):
            data["candidate_rankings"] = []
        if not isinstance(data.get("candidate_ranking_summary"), dict):
            data["candidate_ranking_summary"] = {
                "candidate_count": len(data["business_patterns"]),
                "ranking_count": len(data["candidate_rankings"]),
            }
        if not isinstance(data.get("commander_learning_tasks"), list):
            data["commander_learning_tasks"] = []
        if not isinstance(data.get("commander_learning_summary"), dict):
            data["commander_learning_summary"] = {
                "task_count": len(data["commander_learning_tasks"]),
                "status": "pending",
            }
        self._refresh_summary(data)
        return data

    def save_state(self, state: dict[str, Any]) -> None:
        state["dry_run"] = True
        state["local_first"] = True
        state["external_api_enabled"] = False
        state["production_actions_enabled"] = False
        state["updated_at"] = now_iso()
        if not isinstance(state.get("business_patterns"), list):
            state["business_patterns"] = []
        state["business_pattern_summary"] = {
            "pattern_count": len(state["business_patterns"]),
            "updated_at": now_iso(),
        }
        if not isinstance(state.get("candidate_rankings"), list):
            state["candidate_rankings"] = []
        state["candidate_ranking_summary"] = {
            "candidate_count": len(state["business_patterns"]),
            "ranking_count": len(state["candidate_rankings"]),
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "updated_at": now_iso(),
        }
        if not isinstance(state.get("commander_learning_tasks"), list):
            state["commander_learning_tasks"] = []
        state["commander_learning_summary"] = {
            "task_count": len(state["commander_learning_tasks"]),
            "status": "pending",
            "review_required": True,
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "updated_at": now_iso(),
        }
        self._refresh_summary(state)
        save_json_atomic(self.path, state)

    def register_source(
        self,
        *,
        name: str,
        source_type: str,
        enabled: bool = True,
        priority: int = 50,
        description: str = "",
        metadata: dict[str, Any] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        require_dry_run(dry_run)
        state = self.load_state()
        registry = SourceRegistry(state.get("sources", []))
        source = registry.register_source(
            name=name,
            source_type=source_type,
            enabled=enabled,
            priority=priority,
            description=description,
            metadata=metadata or {},
            dry_run=True,
        )
        state["sources"] = registry.list_sources()
        self.save_state(state)
        return source

    def save_knowledge(
        self,
        *,
        title: str,
        summary: str,
        source: dict[str, Any] | str,
        docs: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        status: str = "saved",
        confidence: int = 50,
        tags: list[str] | None = None,
        business_category: str = "uncategorized",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        require_dry_run(dry_run)
        state = self.load_state()
        record = KnowledgeRecord(
            title=title,
            summary=summary,
            source=source,
            docs=docs or [],
            metadata=metadata or {},
            status=status,
            confidence=confidence,
            tags=tags or [],
            business_category=business_category,
            dry_run=True,
        ).to_dict()
        state.setdefault("knowledge", []).insert(0, record)
        state["knowledge"] = state["knowledge"][:1000]
        self.save_state(state)
        return record

    def load_knowledge(self, knowledge_id: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        state = self.load_state()
        knowledge = list(state.get("knowledge", []))
        if knowledge_id is None:
            return knowledge
        return next((dict(row) for row in knowledge if row.get("knowledge_id") == knowledge_id), {})

    def list_sources(self) -> list[dict[str, Any]]:
        return SourceRegistry(self.load_state().get("sources", [])).list_sources()

    # Phase 118 additive document storage. This is intentionally separate from
    # the legacy Learning Engine state and is never synchronized automatically.
    def load_documents(self, path: str | Path = LEARNING_STORE_PATH) -> list[dict[str, Any]]:
        state = load_json(Path(path), default={})
        if not isinstance(state, dict) or not isinstance(state.get("documents", []), list):
            return []
        return [dict(item) for item in state.get("documents", []) if isinstance(item, dict)]

    def save_document(self, document: dict[str, Any], path: str | Path = LEARNING_STORE_PATH) -> dict[str, Any]:
        from src.learning_engine.knowledge_models import KnowledgeDocument

        item = KnowledgeDocument(**document).to_dict()
        state = load_json(Path(path), default={})
        if not isinstance(state, dict):
            state = {}
        documents = [row for row in state.get("documents", []) if isinstance(row, dict)]
        documents = [row for row in documents if row.get("document_id") != item.get("document_id")]
        documents.append(item)
        state.update({"schema_version": 1, "documents": documents, "automatic_sync": False,
                      "external_request_sent": False, "production_actions_enabled": False})
        save_json_atomic(Path(path), state)
        return dict(item)

    @staticmethod
    def _refresh_summary(state: dict[str, Any]) -> None:
        knowledge = list(state.get("knowledge", []) or [])
        sources = list(state.get("sources", []) or [])
        status_counts: dict[str, int] = {}
        for record in knowledge:
            status = str(record.get("status", "unknown") or "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        state["summary"] = {
            "source_count": len(sources),
            "knowledge_count": len(knowledge),
            "status_counts": status_counts,
            "updated_at": now_iso(),
        }
