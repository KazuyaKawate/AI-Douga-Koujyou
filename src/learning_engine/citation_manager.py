from __future__ import annotations

from typing import Any

from src.learning_engine.knowledge_models import KnowledgeCitation


class CitationManager:
    def create(self, *, source_id: str, locator: str = "", label: str = "") -> dict[str, Any]:
        return KnowledgeCitation(source_id=source_id, locator=locator, label=label).to_dict()

    def validate(self, citation: dict[str, Any], sources: dict[str, dict[str, Any]]) -> bool:
        return bool(citation.get("citation_id") and citation.get("source_id") in sources)
