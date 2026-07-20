from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4


SourceType = Literal["youtube", "note", "web", "pdf", "github", "markdown"]
SOURCE_TYPES: tuple[str, ...] = ("youtube", "note", "web", "pdf", "github", "markdown")
KNOWLEDGE_STATUSES: tuple[str, ...] = ("draft", "saved", "review_required", "archived")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def require_dry_run(dry_run: bool) -> None:
    if dry_run is not True:
        raise ValueError("Learning Engine requires dry_run=True.")


def normalize_source_type(source_type: str) -> str:
    normalized = str(source_type or "").strip().lower()
    if normalized not in SOURCE_TYPES:
        raise ValueError(f"Unsupported learning source type: {source_type}")
    return normalized


def clamp_confidence(value: int | float) -> int:
    return max(0, min(100, int(value)))


@dataclass(frozen=True)
class LearningSource:
    name: str
    type: SourceType
    enabled: bool = True
    priority: int = 50
    description: str = ""
    source_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    local_first: bool = True
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        require_dry_run(self.dry_run)
        source_type = normalize_source_type(self.type)
        return {
            "source_id": self.source_id or f"lsrc-{uuid4().hex[:10]}",
            "name": str(self.name or source_type).strip(),
            "type": source_type,
            "enabled": bool(self.enabled),
            "priority": int(self.priority),
            "description": str(self.description or ""),
            "metadata": dict(self.metadata or {}),
            "dry_run": True,
            "local_first": True,
            "created_at": self.created_at or now_iso(),
        }


@dataclass(frozen=True)
class KnowledgeRecord:
    title: str
    source: dict[str, Any] | str
    summary: str
    docs: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "saved"
    confidence: int = 50
    tags: list[str] = field(default_factory=list)
    business_category: str = "uncategorized"
    knowledge_id: str = ""
    dry_run: bool = True
    local_first: bool = True
    review_required: bool = True
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        require_dry_run(self.dry_run)
        status = str(self.status or "saved").strip().lower()
        if status not in KNOWLEDGE_STATUSES:
            raise ValueError(f"Unsupported knowledge status: {self.status}")
        title = str(self.title or "").strip()
        summary = str(self.summary or "").strip()
        if not title:
            raise ValueError("Knowledge title is required.")
        if not summary:
            raise ValueError("Knowledge summary is required.")
        return {
            "knowledge_id": self.knowledge_id or f"lkn-{uuid4().hex[:10]}",
            "docs": list(self.docs or []),
            "metadata": dict(self.metadata or {}),
            "summary": summary,
            "source": self.source,
            "title": title,
            "created_at": self.created_at or now_iso(),
            "status": status,
            "confidence": clamp_confidence(self.confidence),
            "tags": [str(tag).strip() for tag in self.tags if str(tag).strip()],
            "business_category": str(self.business_category or "uncategorized").strip(),
            "dry_run": True,
            "local_first": True,
            "review_required": True,
        }
