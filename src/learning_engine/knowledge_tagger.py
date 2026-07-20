from __future__ import annotations

from typing import Any

from src.learning_engine.knowledge_models import KnowledgeTag


class KnowledgeTagger:
    def tag(self, document: dict[str, Any], tags: list[str]) -> dict[str, Any]:
        result = dict(document)
        existing = {str(tag.get("name", "")): dict(tag) for tag in result.get("tags", [])}
        for name in tags:
            tag = KnowledgeTag(name=name).to_dict()
            existing[tag["name"]] = tag
        result["tags"] = [existing[key] for key in sorted(existing)]
        return result
