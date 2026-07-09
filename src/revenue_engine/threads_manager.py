from __future__ import annotations

from typing import Any


class ThreadsManager:
    def queue(self, opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "title": item.get("title", ""),
                "post_plan": item.get("next_action", ""),
                "automation_rate": item.get("automation_rate", 0),
                "revenue_score": item.get("revenue_score", 0),
            }
            for item in opportunities
            if item.get("channel") == "threads"
        ]
