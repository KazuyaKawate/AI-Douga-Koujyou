from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.learning_engine.learning_models import clamp_confidence, now_iso, require_dry_run


BusinessCategory = Literal[
    "Affiliate",
    "SNS",
    "Content",
    "Website",
    "Automation",
    "Programming",
    "AI",
    "Marketing",
    "Business",
    "Other",
]
Difficulty = Literal["Easy", "Medium", "Hard"]

BUSINESS_CATEGORIES: tuple[str, ...] = (
    "Affiliate",
    "SNS",
    "Content",
    "Website",
    "Automation",
    "Programming",
    "AI",
    "Marketing",
    "Business",
    "Other",
)
DIFFICULTIES: tuple[str, ...] = ("Easy", "Medium", "Hard")


def normalize_category(value: str) -> str:
    cleaned = str(value or "").strip()
    for category in BUSINESS_CATEGORIES:
        if cleaned.lower() == category.lower():
            return category
    return "Other"


def normalize_difficulty(value: str) -> str:
    cleaned = str(value or "").strip().title()
    return cleaned if cleaned in DIFFICULTIES else "Medium"


@dataclass(frozen=True)
class KnowledgeSummary:
    summary: str
    keywords: list[str] = field(default_factory=list)
    category: BusinessCategory = "Other"
    difficulty: Difficulty = "Medium"
    reproducibility_score: int = 0
    estimated_value: int = 0
    action_items: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    confidence: int = 50
    dry_run: bool = True
    local_first: bool = True
    generated_by: str = "rule_based_summary_engine"
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        require_dry_run(self.dry_run)
        return {
            "summary": str(self.summary or "").strip(),
            "keywords": [str(item).strip() for item in self.keywords if str(item).strip()],
            "category": normalize_category(self.category),
            "difficulty": normalize_difficulty(self.difficulty),
            "reproducibility_score": clamp_confidence(self.reproducibility_score),
            "estimated_value": clamp_confidence(self.estimated_value),
            "action_items": [str(item).strip() for item in self.action_items if str(item).strip()],
            "risks": [str(item).strip() for item in self.risks if str(item).strip()],
            "confidence": clamp_confidence(self.confidence),
            "dry_run": True,
            "local_first": True,
            "generated_by": self.generated_by,
            "created_at": self.created_at or now_iso(),
        }
