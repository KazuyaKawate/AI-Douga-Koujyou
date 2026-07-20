from __future__ import annotations

import re
from typing import Any

from src.learning_engine.candidate_ranking_models import CandidateRanking, priority_score
from src.learning_engine.learning_models import clamp_confidence, require_dry_run


CURRENT_AIOS_CHANNELS = {"note", "Threads", "Website"}
HIGH_RISK_MARKERS: tuple[tuple[str, int], ...] = (
    ("API依存", 18),
    ("広告依存", 16),
    ("法規制", 20),
    ("手作業過多", 12),
    ("再現性低", 14),
    ("情報不足", 10),
)
LOW_PRIORITY_MARKERS = ("video", "動画", "production", "large feature", "大型機能", "deploy", "本番")


class CandidateRankingEngine:
    """Rank local business pattern candidates for first-revenue priority."""

    def rank_candidates(
        self,
        candidates: list[dict[str, Any]],
        *,
        dry_run: bool = True,
    ) -> list[dict[str, Any]]:
        require_dry_run(dry_run)
        scored = [self.score_candidate(candidate, index=index) for index, candidate in enumerate(candidates)]
        ordered = sorted(
            scored,
            key=lambda item: (
                -int(item["_sort_total_score"]),
                int(item["_sort_first_profit_days"]),
                int(item["_sort_initial_cost"]),
                str(item["candidate_id"]),
            ),
        )
        ranked: list[dict[str, Any]] = []
        for rank, item in enumerate(ordered, start=1):
            item["rank"] = rank
            item.pop("_sort_total_score", None)
            item.pop("_sort_first_profit_days", None)
            item.pop("_sort_initial_cost", None)
            ranked.append(item)
        return ranked

    def score_candidate(self, candidate: dict[str, Any], *, index: int = 0) -> dict[str, Any]:
        report = self._report(candidate)
        candidate_id = self._candidate_id(candidate, index)
        candidate_name = str(candidate.get("name") or candidate.get("candidate_name") or "Untitled Candidate")
        risks = self._risks(candidate)
        channels = self._channels(candidate)
        first_profit_days = self._int_value(report, candidate, "estimated_first_profit_days", 90)
        initial_cost = self._int_value(report, candidate, "estimated_initial_cost", 999999)
        automation_ratio = self._int_value(report, candidate, "automation_ratio", 0)
        manual_work_ratio = self._int_value(report, candidate, "manual_work_ratio", 100)
        reproducibility_score = self._int_value(report, candidate, "reproducibility_score", 0)
        estimated_value = self._int_value(report, candidate, "estimated_value", 0)
        confidence = self._int_value(report, candidate, "confidence", 0)
        aios_priority = str(report.get("aios_priority") or candidate.get("aios_priority") or "LOW")
        compatible = bool(report.get("compatible_with_current_aios", candidate.get("compatible_with_current_aios", False)))
        recommended_phase = str(
            report.get("recommended_current_phase")
            or candidate.get("recommended_current_phase")
            or "Phase6-4 Candidate Ranking Review"
        )

        revenue_speed_score = self.score_revenue_speed(first_profit_days)
        cost_score = self.score_cost(initial_cost)
        automation_score = clamp_confidence(automation_ratio)
        compatibility_score = self.score_compatibility(compatible, channels, recommended_phase)
        channel_score = self.score_channel_fit(channels, recommended_phase)
        risk_penalty = self.score_risk_penalty(
            risks=risks,
            candidate_name=candidate_name,
            manual_work_ratio=manual_work_ratio,
            channels=channels,
        )
        total_score = self.score_total(
            revenue_speed_score=revenue_speed_score,
            cost_score=cost_score,
            compatibility_score=compatibility_score,
            channel_score=channel_score,
            automation_score=automation_score,
            reproducibility_score=reproducibility_score,
            aios_priority_score=priority_score(aios_priority),
            estimated_value=estimated_value,
            confidence=confidence,
            risk_penalty=risk_penalty,
        )
        ranking = CandidateRanking(
            rank=1,
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            total_score=total_score,
            revenue_speed_score=revenue_speed_score,
            cost_score=cost_score,
            automation_score=automation_score,
            reproducibility_score=reproducibility_score,
            compatibility_score=compatibility_score,
            risk_penalty=risk_penalty,
            priority_reason=self.build_priority_reason(
                first_profit_days=first_profit_days,
                initial_cost=initial_cost,
                channels=channels,
                compatible=compatible,
                risks=risks,
            ),
            recommended_action=self.recommended_action(total_score, risk_penalty, compatible, recommended_phase),
            recommended_current_phase=recommended_phase,
            dry_run=True,
        ).to_dict()
        ranking["_sort_total_score"] = total_score
        ranking["_sort_first_profit_days"] = first_profit_days
        ranking["_sort_initial_cost"] = initial_cost
        return ranking

    def score_revenue_speed(self, days: int) -> int:
        if days <= 7:
            return 100
        if days >= 90:
            return 0
        return clamp_confidence(100 - int((days - 7) * 100 / 83))

    def score_cost(self, cost: int) -> int:
        if cost <= 0:
            return 100
        if cost >= 10000:
            return 0
        return clamp_confidence(100 - int(cost / 100))

    def score_compatibility(self, compatible: bool, channels: list[str], recommended_phase: str) -> int:
        score = 70 if compatible else 15
        if any(channel in CURRENT_AIOS_CHANNELS for channel in channels):
            score += 20
        if "Phase7" in recommended_phase:
            score += 10
        return clamp_confidence(score)

    def score_channel_fit(self, channels: list[str], recommended_phase: str) -> int:
        score = sum(25 for channel in channels if channel in CURRENT_AIOS_CHANNELS)
        if "note" in recommended_phase:
            score += 10
        if "Threads" in recommended_phase:
            score += 10
        if "Official Site" in recommended_phase or "Website" in recommended_phase:
            score += 10
        return clamp_confidence(score)

    def score_risk_penalty(
        self,
        *,
        risks: list[str],
        candidate_name: str,
        manual_work_ratio: int,
        channels: list[str],
    ) -> int:
        penalty = 0
        risk_text = " ".join(risks)
        for marker, value in HIGH_RISK_MARKERS:
            if marker in risk_text:
                penalty += value
        if manual_work_ratio >= 85:
            penalty += 10
        lower_name = candidate_name.lower()
        if any(marker in lower_name for marker in LOW_PRIORITY_MARKERS):
            penalty += 28
        if "YouTube" in channels:
            penalty += 12
        return min(80, penalty)

    def score_total(
        self,
        *,
        revenue_speed_score: int,
        cost_score: int,
        compatibility_score: int,
        channel_score: int,
        automation_score: int,
        reproducibility_score: int,
        aios_priority_score: int,
        estimated_value: int,
        confidence: int,
        risk_penalty: int,
    ) -> int:
        score = (
            revenue_speed_score * 0.30
            + cost_score * 0.18
            + compatibility_score * 0.16
            + channel_score * 0.11
            + automation_score * 0.08
            + reproducibility_score * 0.08
            + aios_priority_score * 0.05
            + estimated_value * 0.03
            + confidence * 0.01
            - risk_penalty
        )
        return clamp_confidence(round(score))

    def build_priority_reason(
        self,
        *,
        first_profit_days: int,
        initial_cost: int,
        channels: list[str],
        compatible: bool,
        risks: list[str],
    ) -> str:
        channel_text = ", ".join(channels) if channels else "no direct channel"
        compatible_text = "AIOS compatible" if compatible else "AIOS compatibility gap"
        risk_text = "no major risk" if not risks else f"{len(risks)} risk note(s)"
        return (
            f"First profit estimate {first_profit_days} days, initial cost {initial_cost}, "
            f"channels {channel_text}, {compatible_text}, {risk_text}."
        )

    def recommended_action(
        self,
        total_score: int,
        risk_penalty: int,
        compatible: bool,
        recommended_phase: str,
    ) -> str:
        if not compatible:
            return "Keep in local review; do not connect to current AIOS workflows."
        if risk_penalty >= 35:
            return "Resolve risk notes locally before first-revenue testing."
        if total_score >= 70:
            return f"Prioritize for manual first-revenue validation in {recommended_phase}."
        if total_score >= 45:
            return "Keep as a secondary candidate after faster low-cost options."
        return "Archive for now unless new evidence improves speed, cost, or compatibility."

    @staticmethod
    def _report(candidate: dict[str, Any]) -> dict[str, Any]:
        report = candidate.get("reproducibility_report")
        return dict(report) if isinstance(report, dict) else {}

    @staticmethod
    def _candidate_id(candidate: dict[str, Any], index: int) -> str:
        value = candidate.get("candidate_id") or candidate.get("pattern_id") or candidate.get("source_knowledge_id")
        if value:
            return str(value)
        cleaned = re.sub(r"[^a-z0-9]+", "-", str(candidate.get("name", "candidate")).lower()).strip("-")
        return f"cand-{index + 1}-{cleaned or 'unknown'}"

    @staticmethod
    def _int_value(report: dict[str, Any], candidate: dict[str, Any], key: str, default: int) -> int:
        value = report.get(key, candidate.get(key, default))
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _risks(candidate: dict[str, Any]) -> list[str]:
        risks = candidate.get("risks", [])
        if not isinstance(risks, list):
            return ["情報不足"]
        return [str(risk).strip() for risk in risks if str(risk).strip()]

    @staticmethod
    def _channels(candidate: dict[str, Any]) -> list[str]:
        channels = candidate.get("channels", [])
        if not isinstance(channels, list):
            return []
        return [str(channel).strip() for channel in channels if str(channel).strip()]
