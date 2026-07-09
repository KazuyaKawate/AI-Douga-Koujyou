from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CommanderRevenuePlanner:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root)
        self.path = self.root / "config" / "commander_revenue_plan.json"

    def update_daily(self, business_queue: list[dict[str, Any]], history_metrics: dict[str, Any]) -> dict[str, Any]:
        data = load_json(self.path, default={}) or {}
        target = int(data.get("daily_revenue_target", 10000) or 10000)
        forecast = int(sum((job.get("business_task") or {}).get("expected_income", 0) for job in business_queue))
        achieved = int(history_metrics.get("cumulative_expected_revenue", 0) or 0)
        plan = {
            "date": date.today().isoformat(),
            "revenue_target": target,
            "achieved_forecast": achieved,
            "queue_forecast": forecast,
            "remaining_target": max(target - achieved, 0),
            "roi_rank": [
                {
                    "job_id": job.get("job_id", ""),
                    "task_type": (job.get("business_task") or {}).get("task_type", ""),
                    "roi": (job.get("business_task") or {}).get("roi", 0),
                    "priority_score": (job.get("business_task") or {}).get("priority_score", 0),
                }
                for job in business_queue[:10]
            ],
            "updated_at": _now(),
        }
        data.update(plan)
        save_json_atomic(self.path, data)
        return plan
