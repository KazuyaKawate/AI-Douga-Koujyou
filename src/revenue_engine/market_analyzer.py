from __future__ import annotations

from typing import Any


MARKET_PRESETS: dict[str, dict[str, Any]] = {
    "threads_fortune": {"search_demand": 64, "competition": 42, "ad_cpc": 65, "growth": 72, "seasonality": 68, "sns_buzz": 88},
    "note_article": {"search_demand": 58, "competition": 48, "ad_cpc": 50, "growth": 62, "seasonality": 55, "sns_buzz": 61},
    "official_site_seo": {"search_demand": 72, "competition": 55, "ad_cpc": 58, "growth": 70, "seasonality": 50, "sns_buzz": 45},
    "ai_tool_intro": {"search_demand": 76, "competition": 66, "ad_cpc": 74, "growth": 83, "seasonality": 52, "sns_buzz": 73},
    "affiliate_lp": {"search_demand": 69, "competition": 61, "ad_cpc": 82, "growth": 65, "seasonality": 57, "sns_buzz": 54},
    "youtube_summary_note": {"search_demand": 63, "competition": 45, "ad_cpc": 48, "growth": 71, "seasonality": 60, "sns_buzz": 70},
    "aios_feature_sale": {"search_demand": 44, "competition": 35, "ad_cpc": 70, "growth": 68, "seasonality": 45, "sns_buzz": 42},
}


class MarketAnalyzer:
    def analyze(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        key = str(opportunity.get("market_key") or opportunity.get("channel") or "note_article")
        preset = MARKET_PRESETS.get(key, MARKET_PRESETS["note_article"])
        market_size = int(round((preset["search_demand"] + preset["ad_cpc"] + preset["growth"] + preset["sns_buzz"]) / 4))
        roi_estimate = int(round((market_size + max(0, 100 - preset["competition"])) / 2))
        return {
            **opportunity,
            "market_analysis": {
                "search_demand": preset["search_demand"],
                "competition": preset["competition"],
                "ad_cpc": preset["ad_cpc"],
                "market_growth": preset["growth"],
                "seasonality": preset["seasonality"],
                "sns_buzz": preset["sns_buzz"],
                "roi_estimate": roi_estimate,
            },
            "market_size": market_size,
            "competition": int(preset["competition"]),
        }
