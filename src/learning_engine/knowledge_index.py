from __future__ import annotations

from typing import Any, Iterable


class KnowledgeIndex:
    """Deterministic, local in-memory metadata index."""

    def __init__(self, documents: Iterable[dict[str, Any]] | None = None) -> None:
        self._documents: dict[str, dict[str, Any]] = {}
        for document in documents or []:
            self.add(document)

    def add(self, document: dict[str, Any]) -> dict[str, Any]:
        item = dict(document)
        document_id = str(item.get("document_id", ""))
        if not document_id:
            raise ValueError("document_id is required.")
        self._documents[document_id] = item
        return dict(item)

    def get(self, document_id: str) -> dict[str, Any]:
        return dict(self._documents.get(document_id, {}))

    def list(self) -> list[dict[str, Any]]:
        return [dict(self._documents[key]) for key in sorted(self._documents)]

    def search(self, query: str = "", *, tags: list[str] | None = None,
               category: str | None = None) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        wanted_tags = {tag.strip().lower() for tag in tags or []}
        results = []
        for item in self.list():
            item_tags = {str(tag.get("name", tag)).lower() for tag in item.get("tags", [])}
            haystack = f"{item.get('title', '')} {item.get('metadata', {})}".lower()
            if needle and needle not in haystack:
                continue
            if wanted_tags and not wanted_tags.issubset(item_tags):
                continue
            if category and item.get("category") != category:
                continue
            results.append(item)
        return results
