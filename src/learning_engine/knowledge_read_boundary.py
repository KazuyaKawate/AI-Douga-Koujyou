from __future__ import annotations

from typing import Any, Mapping

from src.knowledge.read_adapter import KnowledgeReadAdapter


class LearningKnowledgeReadBoundary:
    """Injected read-only boundary; it cannot write Knowledge files or invoke external systems."""

    def __init__(self, adapter: KnowledgeReadAdapter) -> None:
        if not isinstance(adapter, KnowledgeReadAdapter):
            raise TypeError("KnowledgeReadAdapter injection is required.")
        self._adapter = adapter

    def search(self, query: str, filters: Mapping[str, Any] | None = None,
               dry_run: bool = True) -> dict[str, Any]:
        return self._adapter.search_knowledge(query, filters, dry_run=dry_run)

    def get(self, entry_id: str, dry_run: bool = True) -> dict[str, Any]:
        return self._adapter.get_knowledge_entry(entry_id, dry_run=dry_run)

    def list(self, filters: Mapping[str, Any] | None = None,
             dry_run: bool = True) -> dict[str, Any]:
        return self._adapter.list_knowledge_entries(filters, dry_run=dry_run)

    def existing_index_documents(self, filters: Mapping[str, Any] | None = None) -> tuple[dict[str, Any], ...]:
        """Project validated entries into the pre-existing KnowledgeIndex input contract."""
        rows = self.list(filters, dry_run=True)["results"]
        return tuple({
            "document_id": row["entry_id"], "title": row["title"],
            "category": row["knowledge_type"], "tags": [],
            "metadata": {"phase_id": row["phase_id"], "decision_id": row["decision_id"],
                         "source_path": row["source_path"], "summary": row["summary"]},
            "execute_allowed": False, "approval_required": True,
            "review_required": True, "dry_run": True,
            "production_actions_enabled": False, "external_request_sent": False,
        } for row in rows)
