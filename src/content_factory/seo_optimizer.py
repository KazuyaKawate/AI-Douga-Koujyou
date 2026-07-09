from __future__ import annotations

from typing import Any


class SEOOptimizer:
    def optimize(self, content: dict[str, Any]) -> dict[str, Any]:
        title = str(content.get("title") or content.get("topic") or "AIOS収益化コンテンツ")
        keyword = (content.get("keywords") or [title])[0]
        return {
            "title": title[:58],
            "description": str(content.get("description") or f"{keyword}の始め方と収益化導線を解説します。")[:120],
            "h_tags": ["H1: " + title, "H2: 結論", "H2: 手順", "H2: FAQ"],
            "faq": content.get("faq", [{"q": f"{keyword}は何から始める？", "a": "小さな投稿と計測から始めます。"}]),
            "schema": {"@type": "Article", "headline": title},
            "ogp": {"title": title, "description": f"{keyword}を実践向けに整理"},
            "internal_links": ["/", "/note", "/revenue"],
            "canonical": f"/content/{str(content.get('content_id', 'draft'))}",
        }
