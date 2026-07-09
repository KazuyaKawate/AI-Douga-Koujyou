from __future__ import annotations

from typing import Any


class AffiliateManager:
    def queue(self, opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "title": item.get("title", ""),
                "channel": "affiliate",
                "expected_revenue": item.get("expected_revenue", 0),
                "next_action": item.get("next_action", ""),
            }
            for item in opportunities
            if item.get("channel") == "affiliate"
        ]
