from __future__ import annotations

from typing import Any

from src.learning_engine.knowledge_retriever import KnowledgeRetriever
from src.learning_engine.knowledge_review import KnowledgeReview


class LearningKnowledgeOrchestrator:
    """Coordinates injected local components; it performs no external action."""

    def __init__(self, *, retriever: KnowledgeRetriever, reviewer: KnowledgeReview) -> None:
        self.retriever = retriever
        self.reviewer = reviewer

    def retrieve_for_review(self, query: str = "", *, limit: int = 10) -> list[dict[str, Any]]:
        return [{"document": item, "review": self.reviewer.review(item)}
                for item in self.retriever.retrieve(query, limit=limit)]
