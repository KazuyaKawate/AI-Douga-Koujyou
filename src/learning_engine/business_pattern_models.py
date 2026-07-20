from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from src.learning_engine.learning_models import clamp_confidence, now_iso, require_dry_run
from src.learning_engine.summary_models import normalize_category


PatternStage = Literal["idea", "validated", "rejected"]
AIOSPriority = Literal["LOW", "MEDIUM", "HIGH"]
PATTERN_STAGES: tuple[str, ...] = ("idea", "validated", "rejected")
AIOS_PRIORITIES: tuple[str, ...] = ("LOW", "MEDIUM", "HIGH")


def normalize_stage(value: str) -> str:
    cleaned = str(value or "").strip().lower()
    return cleaned if cleaned in PATTERN_STAGES else "idea"


def normalize_aios_priority(value: str) -> str:
    cleaned = str(value or "").strip().upper()
    return cleaned if cleaned in AIOS_PRIORITIES else "MEDIUM"


@dataclass(frozen=True)
class BusinessPattern:
    name: str
    source_knowledge_id: str
    category: str = "Other"
    monetization_model: str = "unknown"
    target_audience: str = "unknown"
    channels: list[str] = field(default_factory=list)
    required_assets: list[str] = field(default_factory=list)
    revenue_hypothesis: str = ""
    validation_plan: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    reproducibility_score: int = 0
    aios_priority: AIOSPriority = "MEDIUM"
    estimated_first_profit_days: int = 30
    estimated_initial_cost: int = 0
    manual_work_ratio: int = 70
    automation_ratio: int = 30
    compatible_with_current_aios: bool = True
    recommended_current_phase: str = "Phase6-3 Business Pattern Review"
    estimated_value: int = 0
    confidence: int = 50
    stage: PatternStage = "idea"
    pattern_id: str = ""
    dry_run: bool = True
    local_first: bool = True
    generated_by: str = "rule_based_business_pattern_engine"
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        require_dry_run(self.dry_run)
        name = str(self.name or "").strip()
        source_knowledge_id = str(self.source_knowledge_id or "").strip()
        if not name:
            raise ValueError("Business pattern name is required.")
        if not source_knowledge_id:
            raise ValueError("Business pattern source_knowledge_id is required.")
        return {
            "pattern_id": self.pattern_id or f"bpat-{uuid4().hex[:10]}",
            "name": name,
            "source_knowledge_id": source_knowledge_id,
            "category": normalize_category(self.category),
            "monetization_model": str(self.monetization_model or "unknown").strip(),
            "target_audience": str(self.target_audience or "unknown").strip(),
            "channels": [str(item).strip() for item in self.channels if str(item).strip()],
            "required_assets": [str(item).strip() for item in self.required_assets if str(item).strip()],
            "revenue_hypothesis": str(self.revenue_hypothesis or "").strip(),
            "validation_plan": [str(item).strip() for item in self.validation_plan if str(item).strip()],
            "action_items": [str(item).strip() for item in self.action_items if str(item).strip()],
            "risks": [str(item).strip() for item in self.risks if str(item).strip()],
            "evidence": [dict(item) for item in self.evidence if isinstance(item, dict)],
            "reproducibility_score": clamp_confidence(self.reproducibility_score),
            "reproducibility_report": {
                "aios_priority": normalize_aios_priority(self.aios_priority),
                "estimated_first_profit_days": max(1, int(self.estimated_first_profit_days)),
                "estimated_initial_cost": max(0, int(self.estimated_initial_cost)),
                "manual_work_ratio": clamp_confidence(self.manual_work_ratio),
                "automation_ratio": clamp_confidence(self.automation_ratio),
                "compatible_with_current_aios": bool(self.compatible_with_current_aios),
                "recommended_current_phase": str(
                    self.recommended_current_phase or "Phase6-3 Business Pattern Review"
                ).strip(),
            },
            "aios_priority": normalize_aios_priority(self.aios_priority),
            "estimated_first_profit_days": max(1, int(self.estimated_first_profit_days)),
            "estimated_initial_cost": max(0, int(self.estimated_initial_cost)),
            "manual_work_ratio": clamp_confidence(self.manual_work_ratio),
            "automation_ratio": clamp_confidence(self.automation_ratio),
            "compatible_with_current_aios": bool(self.compatible_with_current_aios),
            "recommended_current_phase": str(
                self.recommended_current_phase or "Phase6-3 Business Pattern Review"
            ).strip(),
            "estimated_value": clamp_confidence(self.estimated_value),
            "confidence": clamp_confidence(self.confidence),
            "stage": normalize_stage(self.stage),
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "generated_by": self.generated_by,
            "created_at": self.created_at or now_iso(),
        }
