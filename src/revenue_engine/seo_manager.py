from __future__ import annotations

from typing import Any


class SEOManager:
    def queue(self, opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "title": item.get("title", ""),
                "seo_action": item.get("next_action", ""),
                "search_demand": item.get("market_analysis", {}).get("search_demand", 0),
                "competition": item.get("market_analysis", {}).get("competition", 0),
            }
            for item in opportunities
            if item.get("channel") in {"official_site", "seo"}
        ]
