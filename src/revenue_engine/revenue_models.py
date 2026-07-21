from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from src.learning_engine.business_pattern_models import normalize_aios_priority
from src.learning_engine.learning_models import clamp_confidence, now_iso, require_dry_run


RevenueCategory = Literal["note", "Threads", "Website", "Affiliate", "Consulting", "Other"]
Difficulty = Literal["Easy", "Medium", "Hard"]

REVENUE_CATEGORIES: tuple[str, ...] = ("note", "Threads", "Website", "Affiliate", "Consulting", "Other")
DIFFICULTIES: tuple[str, ...] = ("Easy", "Medium", "Hard")


def normalize_revenue_category(value: str) -> str:
    cleaned = str(value or "").strip()
    lower = cleaned.lower()
    if lower == "threads":
        return "Threads"
    if lower in {"note", "website", "affiliate", "consulting"}:
        return "Website" if lower == "website" else cleaned.title() if lower != "note" else "note"
    for category in REVENUE_CATEGORIES:
        if cleaned == category:
            return category
    return "Other"


def normalize_difficulty(value: str) -> str:
    cleaned = str(value or "").strip().title()
    return cleaned if cleaned in DIFFICULTIES else "Medium"


@dataclass(frozen=True)
class RevenuePlan:
    task_id: str
    title: str
    expected_profit: int
    estimated_first_profit_days: int
    estimated_monthly_profit: int
    estimated_initial_cost: int
    difficulty: str
    automation_ratio: int
    manual_ratio: int
    required_engines: list[str] = field(default_factory=list)
    required_review: bool = True
    status: str = "planned"
    business_category: str = "Other"
    priority: str = "MEDIUM"
    confidence: int = 50
    risk: list[str] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    plan_id: str = ""
    dry_run: bool = True
    local_first: bool = True
    external_api_enabled: bool = False
    production_actions_enabled: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        require_dry_run(self.dry_run)
        return {
            "plan_id": self.plan_id or f"rev-plan-{uuid4().hex[:10]}",
            "task_id": str(self.task_id or "").strip(),
            "title": str(self.title or "Untitled Revenue Plan").strip(),
            "expected_profit": max(0, int(self.expected_profit)),
            "estimated_first_profit_days": max(1, int(self.estimated_first_profit_days)),
            "estimated_monthly_profit": max(0, int(self.estimated_monthly_profit)),
            "estimated_initial_cost": max(0, int(self.estimated_initial_cost)),
            "difficulty": normalize_difficulty(self.difficulty),
            "automation_ratio": clamp_confidence(self.automation_ratio),
            "manual_ratio": clamp_confidence(self.manual_ratio),
            "required_engines": [str(item).strip() for item in self.required_engines if str(item).strip()],
            "required_review": True,
            "status": "planned",
            "business_category": normalize_revenue_category(self.business_category),
            "priority": normalize_aios_priority(self.priority),
            "confidence": clamp_confidence(self.confidence),
            "risk": [str(item).strip() for item in self.risk if str(item).strip()],
            "source": dict(self.source or {}),
            "review_required": True,
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "created_at": self.created_at or now_iso(),
        }
