from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.learning_engine.business_pattern_models import normalize_aios_priority
from src.learning_engine.learning_models import clamp_confidence, now_iso, require_dry_run


@dataclass(frozen=True)
class CandidateRanking:
    rank: int
    candidate_id: str
    candidate_name: str
    total_score: int
    revenue_speed_score: int
    cost_score: int
    automation_score: int
    reproducibility_score: int
    compatibility_score: int
    risk_penalty: int
    priority_reason: str
    recommended_action: str
    recommended_current_phase: str
    review_required: bool = True
    dry_run: bool = True
    local_first: bool = True
    external_api_enabled: bool = False
    production_actions_enabled: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        require_dry_run(self.dry_run)
        return {
            "rank": max(1, int(self.rank)),
            "candidate_id": str(self.candidate_id or "").strip(),
            "candidate_name": str(self.candidate_name or "Untitled Candidate").strip(),
            "total_score": clamp_confidence(self.total_score),
            "revenue_speed_score": clamp_confidence(self.revenue_speed_score),
            "cost_score": clamp_confidence(self.cost_score),
            "automation_score": clamp_confidence(self.automation_score),
            "reproducibility_score": clamp_confidence(self.reproducibility_score),
            "compatibility_score": clamp_confidence(self.compatibility_score),
            "risk_penalty": max(0, int(self.risk_penalty)),
            "priority_reason": str(self.priority_reason or "").strip(),
            "recommended_action": str(self.recommended_action or "Review manually before use.").strip(),
            "recommended_current_phase": str(
                self.recommended_current_phase or "Phase6-4 Candidate Ranking Review"
            ).strip(),
            "review_required": True,
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "created_at": self.created_at or now_iso(),
        }


def priority_score(value: str) -> int:
    priority = normalize_aios_priority(value)
    return {"HIGH": 100, "MEDIUM": 62, "LOW": 25}[priority]
