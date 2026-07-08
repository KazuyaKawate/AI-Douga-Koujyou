from __future__ import annotations

from typing import Any

from src.coding_engine.revenue_gate import CommanderRevenueGate


ALLOWED_REVENUE_AREAS = {
    "seo": ("seo", "検索", "流入"),
    "threads": ("threads", "実投稿", "投稿"),
    "note": ("note", "note売上", "有料note"),
    "lp": ("lp", "landing", "ランディング", "導線"),
    "affiliate": ("affiliate", "アフィリエイト", "クリック"),
}
FORBIDDEN_LARGE_WORK = ("大型", "全面刷新", "全体リファクタ", "新規プラットフォーム", "マルチユーザー", "クラウド移行")


class ROIFirstScheduler:
    def __init__(self) -> None:
        self.gate = CommanderRevenueGate()

    def evaluate(self, job: dict[str, Any]) -> dict[str, Any]:
        instruction = str(job.get("instruction", ""))
        text = instruction.lower()
        areas = [name for name, tokens in ALLOWED_REVENUE_AREAS.items() if any(token.lower() in text for token in tokens)]
        gate = self.gate.evaluate(instruction, job.get("metadata", {}).get("target_files", []))
        forbidden = any(token.lower() in text for token in FORBIDDEN_LARGE_WORK)
        allowed = bool(areas) and not forbidden and gate.get("decision") != "defer"
        return {
            "allowed": allowed,
            "areas": areas,
            "forbidden_large_work": forbidden,
            "revenue_gate": gate,
            "decision": "process" if allowed else "defer",
            "reason": "収益改善Jobとして処理します。" if allowed else "初収益への距離が遠い、または大型改善のため延期します。",
        }
