from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from src.learning_engine.business_pattern_models import normalize_aios_priority
from src.learning_engine.learning_models import clamp_confidence, now_iso, require_dry_run


TaskStatus = Literal["pending"]


@dataclass(frozen=True)
class CommanderLearningTask:
    title: str
    description: str
    priority: str
    estimated_profit_days: int
    estimated_initial_cost: int
    automation_ratio: int
    manual_ratio: int
    recommended_phase: str
    source: dict[str, Any]
    confidence: int
    risk: list[str] = field(default_factory=list)
    business_category: str = "Other"
    status: TaskStatus = "pending"
    task_id: str = ""
    review_required: bool = True
    dry_run: bool = True
    local_first: bool = True
    external_api_enabled: bool = False
    production_actions_enabled: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        require_dry_run(self.dry_run)
        return {
            "task_id": self.task_id or f"cmd-learn-{uuid4().hex[:10]}",
            "title": str(self.title or "Untitled Commander Task").strip(),
            "description": str(self.description or "").strip(),
            "priority": normalize_aios_priority(self.priority),
            "estimated_profit_days": max(1, int(self.estimated_profit_days)),
            "estimated_initial_cost": max(0, int(self.estimated_initial_cost)),
            "automation_ratio": clamp_confidence(self.automation_ratio),
            "manual_ratio": clamp_confidence(self.manual_ratio),
            "recommended_phase": str(self.recommended_phase or "Phase6-5 Commander Review").strip(),
            "source": dict(self.source or {}),
            "confidence": clamp_confidence(self.confidence),
            "risk": [str(item).strip() for item in self.risk if str(item).strip()],
            "business_category": str(self.business_category or "Other").strip(),
            "status": "pending",
            "review_required": True,
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "created_at": self.created_at or now_iso(),
        }


def commander_priority_weight(priority: str) -> int:
    normalized = normalize_aios_priority(priority)
    return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}[normalized]
