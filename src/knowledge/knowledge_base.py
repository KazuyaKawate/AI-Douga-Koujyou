from __future__ import annotations

from pathlib import Path
from typing import Any

from src.creator_factory.factory_manager import KNOWLEDGE_TYPES, CreatorFactoryManager


class KnowledgeBase:
    """Thin local-only facade for reusable Creator Factory knowledge."""

    def __init__(self, data_root: str | Path | None = None) -> None:
        self.manager = CreatorFactoryManager(data_root) if data_root is not None else CreatorFactoryManager()

    def add(self, title: str, knowledge_type: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
        return self.manager.add_knowledge_item(title, knowledge_type, content, tags=tags)

    def list(self, knowledge_type: str | None = None) -> list[dict[str, Any]]:
        return self.manager.list_knowledge(knowledge_type)

    def types(self) -> list[str]:
        return list(KNOWLEDGE_TYPES)
