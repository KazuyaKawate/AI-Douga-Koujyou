from __future__ import annotations

from typing import Any


class ContentAnalytics:
    def summarize(self, contents: list[dict[str, Any]], metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        metrics = metrics or {}
        pv = int(metrics.get("pv", max(len(contents) * 120, 1)))
        ctr = float(metrics.get("ctr", 0.04))
        cvr = float(metrics.get("cvr", 0.015))
        revenue = int(metrics.get("revenue", sum(int(item.get("estimated_revenue", 0)) for item in contents)))
        roi = int(metrics.get("roi", revenue / max(len(contents) * 1000, 1) * 100))
        return {
            "pv": pv,
            "ctr": ctr,
            "cvr": cvr,
            "revenue": revenue,
            "stay_time": float(metrics.get("stay_time", 72.0)),
            "click_rate": ctr,
            "roi": roi,
            "improvement_candidates": self.improvements(pv, ctr, cvr, revenue),
        }

    @staticmethod
    def improvements(pv: int, ctr: float, cvr: float, revenue: int) -> list[str]:
        ideas = []
        if ctr < 0.05:
            ideas.append("CTAを本文中盤と末尾に追加する")
        if cvr < 0.02:
            ideas.append("比較表とFAQを追加して不安を減らす")
        if revenue <= 0:
            ideas.append("Affiliateまたは有料note導線を追加する")
        if pv < 300:
            ideas.append("Threads投稿本数を増やして流入を作る")
        return ideas or ["勝ちパターンを次の投稿へ横展開する"]
