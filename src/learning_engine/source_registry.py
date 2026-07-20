from __future__ import annotations

from typing import Any

from src.learning_engine.learning_models import LearningSource, SOURCE_TYPES, normalize_source_type


DEFAULT_SOURCE_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "YouTube",
        "type": "youtube",
        "enabled": False,
        "priority": 20,
        "description": "Manual transcript or exported metadata only. No external API access.",
    },
    {
        "name": "note",
        "type": "note",
        "enabled": True,
        "priority": 60,
        "description": "Manually saved note article text or metadata.",
    },
    {
        "name": "Web Article",
        "type": "web",
        "enabled": True,
        "priority": 50,
        "description": "Manually saved web article Markdown or plain text.",
    },
    {
        "name": "PDF",
        "type": "pdf",
        "enabled": True,
        "priority": 40,
        "description": "Local PDF-derived text. No remote download.",
    },
    {
        "name": "GitHub",
        "type": "github",
        "enabled": False,
        "priority": 30,
        "description": "Local clone or manually exported repository documents only.",
    },
    {
        "name": "Local Markdown",
        "type": "markdown",
        "enabled": True,
        "priority": 80,
        "description": "Primary Local First source for Phase6-1.",
    },
)


class SourceRegistry:
    def __init__(self, sources: list[dict[str, Any]] | None = None) -> None:
        self._sources = [self._normalize(row) for row in (sources or list(DEFAULT_SOURCE_DEFINITIONS))]

    def list_sources(self) -> list[dict[str, Any]]:
        return sorted((dict(row) for row in self._sources), key=lambda row: int(row.get("priority", 0)), reverse=True)

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
        source = LearningSource(
            name=name,
            type=normalize_source_type(source_type),  # type: ignore[arg-type]
            enabled=enabled,
            priority=priority,
            description=description,
            metadata=metadata or {},
            dry_run=dry_run,
        ).to_dict()
        self._upsert(source)
        return dict(source)

    def find_by_type(self, source_type: str) -> dict[str, Any] | None:
        normalized = normalize_source_type(source_type)
        return next((dict(row) for row in self._sources if row.get("type") == normalized), None)

    def merge_registered_sources(self, sources: list[dict[str, Any]]) -> None:
        for source in sources:
            self._upsert(self._normalize(source))

    def _upsert(self, source: dict[str, Any]) -> None:
        source_type = source["type"]
        self._sources = [row for row in self._sources if row.get("type") != source_type]
        self._sources.append(source)

    @staticmethod
    def _normalize(source: dict[str, Any]) -> dict[str, Any]:
        return LearningSource(
            source_id=str(source.get("source_id", "")),
            name=str(source.get("name") or source.get("type") or "source"),
            type=normalize_source_type(str(source.get("type", ""))),  # type: ignore[arg-type]
            enabled=bool(source.get("enabled", True)),
            priority=int(source.get("priority", 50) or 0),
            description=str(source.get("description", "")),
            metadata=dict(source.get("metadata", {}) or {}),
            dry_run=bool(source.get("dry_run", True)),
            created_at=str(source.get("created_at", "")),
        ).to_dict()
