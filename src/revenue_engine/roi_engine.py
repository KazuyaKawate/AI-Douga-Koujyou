from __future__ import annotations

from typing import Any


RISK_PENALTY = {"low": 1.0, "medium": 0.82, "normal": 0.82, "high": 0.55, "blocked": 0.0}


class ROIEngine:
    """Score revenue actions with ROI-first, risk-aware economics."""

    def score(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        expected_revenue = max(int(opportunity.get("expected_revenue", 0) or 0), 0)
        expected_profit = max(int(opportunity.get("expected_profit", expected_revenue) or 0), 0)
        effort_hours = max(float(opportunity.get("effort_hours", 1) or 1), 0.5)
        cost = max(int(opportunity.get("estimated_cost", effort_hours * 1200) or 0), 1)
        roi = round((expected_profit - cost) / cost * 100, 1)
        payback_days = max(int(opportunity.get("payback_days", 7) or 7), 1)
        risk = str(opportunity.get("risk", "medium")).lower()

        revenue_score = self._scale(expected_revenue, 50000)
        profit_score = self._scale(expected_profit, 40000)
        roi_score = self._scale(max(roi, 0), 600)
        difficulty_score = max(0, 100 - int(opportunity.get("difficulty", 50) or 50))
        effort_score = max(0, 100 - min(int(effort_hours * 10), 100))
        market_score = int(opportunity.get("market_size", 50) or 50)
        competition_score = max(0, 100 - int(opportunity.get("competition", 50) or 50))
        continuity_score = int(opportunity.get("continuity", 50) or 50)
        automation_score = int(opportunity.get("automation_rate", 50) or 50)
        risk_multiplier = RISK_PENALTY.get(risk, 0.75)

        weighted = (
            roi_score * 0.22
            + revenue_score * 0.16
            + profit_score * 0.16
            + difficulty_score * 0.09
            + effort_score * 0.09
            + market_score * 0.1
            + competition_score * 0.07
            + continuity_score * 0.06
            + automation_score * 0.05
        )
        revenue_score_total = int(round(max(0, min(100, weighted * risk_multiplier))))
        return {
            **opportunity,
            "expected_revenue": expected_revenue,
            "expected_profit": expected_profit,
            "estimated_cost": cost,
            "effort_hours": effort_hours,
            "roi": roi,
            "payback_days": payback_days,
            "risk": risk,
            "score_breakdown": {
                "roi": roi_score,
                "revenue": revenue_score,
                "profit": profit_score,
                "difficulty": difficulty_score,
                "effort": effort_score,
                "market_size": market_score,
                "competition": competition_score,
                "continuity": continuity_score,
                "automation": automation_score,
                "risk_multiplier": risk_multiplier,
            },
            "revenue_score": revenue_score_total,
            "decision": "execute" if revenue_score_total >= 70 and risk != "blocked" else "watch" if revenue_score_total >= 45 else "defer",
        }

    def rank(self, opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored = [self.score(item) for item in opportunities if str(item.get("risk", "")).lower() != "blocked"]
        return sorted(
            scored,
            key=lambda item: (
                -int(item.get("revenue_score", 0)),
                int(item.get("payback_days", 999)),
                float(item.get("effort_hours", 999)),
                -int(item.get("expected_profit", 0)),
            ),
        )

    @staticmethod
    def _scale(value: float, max_value: float) -> int:
        return int(round(max(0, min(100, value / max(max_value, 1) * 100))))
