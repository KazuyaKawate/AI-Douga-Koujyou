from __future__ import annotations

from typing import Any

from src.learning_engine.knowledge_index import KnowledgeIndex


class KnowledgeRetriever:
    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def retrieve(self, query: str = "", *, tags: list[str] | None = None,
                 category: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        return self.index.search(query, tags=tags, category=category)[:max(0, int(limit))]
