from __future__ import annotations

from datetime import datetime
from typing import Any


class AnalyticsSync:
    def sync(self, item: dict[str, Any]) -> dict[str, Any]:
        content = item.get("content", {})
        base = max(len(str(content.get("text") or content.get("body") or content.get("title", ""))), 1)
        pv = max(20, base // 4)
        ctr = 0.04
        cvr = 0.012
        revenue = int(item.get("content", {}).get("estimated_revenue", 0) or pv * ctr * 120)
        roi = int(revenue / max(500, 1) * 100)
        return {
            "pv": pv,
            "ctr": ctr,
            "cvr": cvr,
            "clicks": int(pv * ctr),
            "impressions": pv * 3,
            "followers_delta": max(0, int(pv * 0.005)),
            "revenue": revenue,
            "roi": roi,
            "synced_at": datetime.now().isoformat(timespec="seconds"),
        }
