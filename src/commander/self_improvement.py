from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CommanderSelfImprovement:
    def record(self, state: dict[str, Any], job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        history = state.get("history", [])
        completed = sum(1 for item in history if item.get("status") == "completed")
        failed = sum(1 for item in history if item.get("status") == "failed")
        total = max(completed + failed, 1)
        metrics = result.get("metrics", {})
        record = {
            "metric_id": f"cmdm-{uuid4().hex[:10]}",
            "job_id": job.get("job_id", ""),
            "success_rate": round(completed / total, 3),
            "roi": int(metrics.get("roi", result.get("revenue_gate", {}).get("score", 0)) or 0),
            "ctr": float(metrics.get("ctr", 0) or 0),
            "cvr": float(metrics.get("cvr", 0) or 0),
            "profit": int(metrics.get("profit", result.get("roi", {}).get("estimated_revenue", 0) if isinstance(result.get("roi"), dict) else 0) or 0),
            "improvement_candidates": self.candidates(result),
            "created_at": _now(),
        }
        state.setdefault("metrics", []).insert(0, record)
        state["metrics"] = state["metrics"][:300]
        return record

    @staticmethod
    def candidates(result: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = []
        gate = result.get("revenue_gate", {})
        if gate.get("decision") == "defer":
            candidates.append({"type": "roi", "instruction": "初収益に近いSEO/Threads/note/affiliate改善へ再スコープする"})
        if result.get("status") == "failed":
            candidates.append({"type": "retry", "instruction": "Provider順序を変更し、fallbackで再実行する"})
        if result.get("coding_run", {}).get("applied_edits", {}).get("status") == "preview_locked":
            candidates.append({"type": "review", "instruction": "Diff Previewを人間レビューしてからapply可否を決める"})
        return candidates[:5]
