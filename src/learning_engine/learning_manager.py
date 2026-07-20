from __future__ import annotations

from pathlib import Path
from typing import Any

from src.learning_engine.knowledge_store import KnowledgeStore, LEARNING_ENGINE_PATH


class LearningManager:
    """Phase6-1 Learning Intake facade.

    The manager only registers local source metadata and saves knowledge records.
    It does not call external APIs, train models, publish content, or touch
    production systems.
    """

    def __init__(self, path: str | Path = LEARNING_ENGINE_PATH) -> None:
        self.store = KnowledgeStore(path=path)

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
        return self.store.register_source(
            name=name,
            source_type=source_type,
            enabled=enabled,
            priority=priority,
            description=description,
            metadata=metadata or {},
            dry_run=dry_run,
        )

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
        return self.store.save_knowledge(
            title=title,
            summary=summary,
            source=source,
            docs=docs or [],
            metadata=metadata or {},
            status=status,
            confidence=confidence,
            tags=tags or [],
            business_category=business_category,
            dry_run=dry_run,
        )

    def load_knowledge(self, knowledge_id: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        return self.store.load_knowledge(knowledge_id)

    def list_sources(self) -> list[dict[str, Any]]:
        return self.store.list_sources()
