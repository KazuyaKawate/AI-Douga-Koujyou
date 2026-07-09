from __future__ import annotations

from typing import Any
from uuid import uuid4


class ABTesting:
    def create(self, content: dict[str, Any]) -> dict[str, Any]:
        title = content.get("title") or content.get("topic") or "AIOS収益化"
        variants = [
            {"variant": "A", "title": title, "cta": content.get("cta", "今日から試す"), "image": "clear"},
            {"variant": "B", "title": f"{title}：失敗しない始め方", "cta": "無料で1本作る", "image": "contrast"},
        ]
        winner = max(variants, key=lambda item: len(item["cta"]) + (5 if "失敗" in item["title"] else 0))
        return {
            "test_id": f"ab-{uuid4().hex[:10]}",
            "content_id": content.get("content_id", ""),
            "variants": variants,
            "dimensions": ["title", "cta", "image", "posting_time"],
            "winner": winner,
            "auto_adopt": True,
        }
