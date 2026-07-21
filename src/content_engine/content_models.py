from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from src.learning_engine.learning_models import clamp_confidence, now_iso, require_dry_run


def trim_text(value: str, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit].rstrip()


@dataclass(frozen=True)
class ContentPlan:
    title: str
    subtitle: str
    summary: str
    note_outline: list[str]
    threads_outline: list[str]
    website_outline: list[str]
    seo_keywords: list[str]
    hashtags: list[str]
    category: str
    target: str
    estimated_read_time: int
    cta: str
    source: dict[str, Any] = field(default_factory=dict)
    content_id: str = ""
    required_review: bool = True
    status: str = "draft"
    dry_run: bool = True
    local_first: bool = True
    external_api_enabled: bool = False
    production_actions_enabled: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        require_dry_run(self.dry_run)
        return {
            "content_id": self.content_id or f"cnt-plan-{uuid4().hex[:10]}",
            "title": trim_text(self.title, 60),
            "subtitle": trim_text(self.subtitle, 90),
            "summary": trim_text(self.summary, 120),
            "note_outline": [str(item).strip() for item in self.note_outline if str(item).strip()],
            "threads_outline": [str(item).strip() for item in self.threads_outline[:20] if str(item).strip()],
            "website_outline": [str(item).strip() for item in self.website_outline if str(item).strip()],
            "seo_keywords": [str(item).strip() for item in self.seo_keywords[:10] if str(item).strip()],
            "hashtags": [self._hashtag(item) for item in self.hashtags[:10] if str(item).strip()],
            "category": str(self.category or "Other").strip(),
            "target": str(self.target or "AIOS revenue reviewers").strip(),
            "estimated_read_time": max(1, int(self.estimated_read_time)),
            "cta": trim_text(self.cta, 120),
            "source": dict(self.source or {}),
            "required_review": True,
            "review_required": True,
            "status": "draft",
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "confidence": clamp_confidence(int(self.source.get("confidence", 50) or 50)),
            "created_at": self.created_at or now_iso(),
        }

    @staticmethod
    def _hashtag(value: str) -> str:
        cleaned = "".join(ch for ch in str(value).strip().replace(" ", "") if ch.isalnum() or ch in {"_", "-"})
        return cleaned if cleaned.startswith("#") else f"#{cleaned}"
