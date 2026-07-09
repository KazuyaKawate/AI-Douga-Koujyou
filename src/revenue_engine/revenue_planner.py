from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RevenuePlanner:
    def build_plan(self, ranked: list[dict[str, Any]]) -> dict[str, Any]:
        today = ranked[:1]
        week = ranked[:3]
        month = ranked[:5]
        quarter = ranked[:8]
        return {
            "plan_date": date.today().isoformat(),
            "today": self._actions(today, "today"),
            "week": self._actions(week, "week"),
            "month": self._actions(month, "month"),
            "quarter": self._actions(quarter, "quarter"),
            "mission_planner_payload": {
                "source": "revenue_engine",
                "status": "ready",
                "top_action": today[0] if today else {},
                "ranked_actions": ranked[:10],
                "created_at": _now(),
            },
            "created_at": _now(),
        }

    @staticmethod
    def _actions(items: list[dict[str, Any]], window: str) -> list[dict[str, Any]]:
        return [
            {
                "window": window,
                "opportunity_id": item.get("opportunity_id", ""),
                "title": item.get("title", ""),
                "channel": item.get("channel", ""),
                "revenue_score": item.get("revenue_score", 0),
                "expected_profit": item.get("expected_profit", 0),
                "roi": item.get("roi", 0),
                "next_action": item.get("next_action", ""),
            }
            for item in items
        ]
