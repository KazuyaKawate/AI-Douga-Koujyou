from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from src.revenue_engine.market_analyzer import MarketAnalyzer
from src.revenue_engine.roi_engine import ROIEngine


INITIAL_OPPORTUNITIES: list[dict[str, Any]] = [
    {
        "priority": 1,
        "title": "Threads占い",
        "channel": "threads",
        "market_key": "threads_fortune",
        "expected_revenue": 24000,
        "expected_profit": 21000,
        "effort_hours": 2,
        "difficulty": 25,
        "risk": "low",
        "continuity": 82,
        "automation_rate": 88,
        "payback_days": 3,
        "next_action": "占い投稿を3本生成し、note導線を付けて投稿予約する",
    },
    {
        "priority": 2,
        "title": "note記事",
        "channel": "note",
        "market_key": "note_article",
        "expected_revenue": 20000,
        "expected_profit": 17500,
        "effort_hours": 3,
        "difficulty": 35,
        "risk": "low",
        "continuity": 78,
        "automation_rate": 80,
        "payback_days": 5,
        "next_action": "収益化テーマでnote記事を1本作成し、Threadsへ展開する",
    },
    {
        "priority": 3,
        "title": "AIOS公式サイトSEO",
        "channel": "official_site",
        "market_key": "official_site_seo",
        "expected_revenue": 26000,
        "expected_profit": 23000,
        "effort_hours": 5,
        "difficulty": 45,
        "risk": "medium",
        "continuity": 86,
        "automation_rate": 65,
        "payback_days": 14,
        "next_action": "公式サイトに収益導線と検索意図ページを追加する",
    },
    {
        "priority": 4,
        "title": "AIツール紹介",
        "channel": "affiliate",
        "market_key": "ai_tool_intro",
        "expected_revenue": 22000,
        "expected_profit": 18500,
        "effort_hours": 4,
        "difficulty": 42,
        "risk": "medium",
        "continuity": 73,
        "automation_rate": 72,
        "payback_days": 7,
        "next_action": "AIツール比較記事とSNS紹介文を生成する",
    },
    {
        "priority": 5,
        "title": "アフィリエイトLP",
        "channel": "affiliate",
        "market_key": "affiliate_lp",
        "expected_revenue": 32000,
        "expected_profit": 26000,
        "effort_hours": 7,
        "difficulty": 58,
        "risk": "medium",
        "continuity": 80,
        "automation_rate": 58,
        "payback_days": 21,
        "next_action": "1商品に絞ったLP構成とCTAを作成する",
    },
    {
        "priority": 6,
        "title": "YouTube要約→note化",
        "channel": "note",
        "market_key": "youtube_summary_note",
        "expected_revenue": 18000,
        "expected_profit": 15500,
        "effort_hours": 3,
        "difficulty": 38,
        "risk": "low",
        "continuity": 70,
        "automation_rate": 78,
        "payback_days": 6,
        "next_action": "需要のある動画を要約し、note記事へ変換する",
    },
]

PROHIBITED_TERMS = ("違法", "グレー", "詐欺", "無断転載", "著作権侵害", "薬機法違反")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class OpportunityEngine:
    def __init__(self) -> None:
        self.market = MarketAnalyzer()
        self.roi = ROIEngine()

    def generate(self, extra_candidates: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        candidates = [dict(item) for item in INITIAL_OPPORTUNITIES]
        candidates.extend(extra_candidates or [])
        safe = [self._prepare(item) for item in candidates if self._allowed(item)]
        analyzed = [self.market.analyze(item) for item in safe]
        return self.roi.rank(analyzed)

    def _prepare(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "opportunity_id": item.get("opportunity_id", f"opp-{uuid4().hex[:10]}"),
            "created_at": item.get("created_at", _now()),
            "constitution": {
                "profit_maximization": True,
                "roi_first": True,
                "long_term_profit": True,
                "illegal_gray_forbidden": True,
                "auto_improvement_required": True,
                "knowledge_required": True,
                "agent_integration_required": True,
            },
            **item,
        }

    @staticmethod
    def _allowed(item: dict[str, Any]) -> bool:
        text = " ".join(str(value) for value in item.values())
        return not any(term in text for term in PROHIBITED_TERMS)
