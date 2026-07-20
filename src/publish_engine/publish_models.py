from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from src.learning_engine.learning_models import clamp_confidence, now_iso, require_dry_run


Platform = Literal["note", "Threads", "Website", "X", "Instagram", "YouTube", "Facebook"]
PLATFORMS: tuple[str, ...] = ("note", "Threads", "Website", "X", "Instagram", "YouTube", "Facebook")


def normalize_platform(value: str) -> str:
    cleaned = str(value or "").strip()
    lower = cleaned.lower()
    if lower == "threads":
        return "Threads"
    if lower == "website":
        return "Website"
    for platform in PLATFORMS:
        if cleaned == platform:
            return platform
    return "note"


def trim_text(value: str, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit].rstrip()


def scheduled_time_for_rank(rank: int, base: datetime | None = None) -> str:
    start = base or datetime.now().replace(microsecond=0)
    return (start + timedelta(hours=max(0, rank - 1) * 3)).isoformat(timespec="seconds")


@dataclass(frozen=True)
class PublishPlan:
    content_id: str
    platform: str
    title: str
    body: str
    hashtags: list[str] = field(default_factory=list)
    seo_title: str = ""
    seo_description: str = ""
    publish_priority: int = 50
    scheduled_time: str = ""
    publish_id: str = ""
    review_required: bool = True
    approval_status: str = "pending_review"
    publish_status: str = "draft"
    retry_count: int = 0
    source: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    local_first: bool = True
    external_api_enabled: bool = False
    production_actions_enabled: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        require_dry_run(self.dry_run)
        return {
            "publish_id": self.publish_id or f"pub-plan-{uuid4().hex[:10]}",
            "content_id": str(self.content_id or "").strip(),
            "platform": normalize_platform(self.platform),
            "title": trim_text(self.title, 80),
            "body": str(self.body or "").strip(),
            "hashtags": [self._hashtag(item) for item in self.hashtags[:12] if str(item).strip()],
            "seo_title": trim_text(self.seo_title or self.title, 60),
            "seo_description": trim_text(self.seo_description or self.body, 120),
            "publish_priority": clamp_confidence(self.publish_priority),
            "scheduled_time": self.scheduled_time or scheduled_time_for_rank(1),
            "review_required": True,
            "required_review": True,
            "approval_status": "pending_review",
            "publish_status": "draft",
            "retry_count": max(0, int(self.retry_count)),
            "source": dict(self.source or {}),
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "created_at": self.created_at or now_iso(),
        }

    @staticmethod
    def _hashtag(value: str) -> str:
        cleaned = "".join(ch for ch in str(value).strip().replace(" ", "") if ch.isalnum() or ch in {"_", "-"})
        return cleaned if cleaned.startswith("#") else f"#{cleaned}"
