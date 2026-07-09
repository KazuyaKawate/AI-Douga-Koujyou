from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CompanyEngine:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root)
        self.path = self.root / "config" / "commander_company.json"

    def update(self, revenue_plan: dict[str, Any] | None = None) -> dict[str, Any]:
        data = load_json(self.path, default={}) or {}
        cash = int(data.get("cash", 0) or 0)
        monthly_cost = int(data.get("monthly_cost", 0) or 0)
        monthly_income = int(data.get("monthly_income", revenue_plan.get("queue_forecast", 0) if revenue_plan else 0) or 0)
        profit = monthly_income - monthly_cost
        runway = 999 if monthly_cost <= 0 else round(cash / monthly_cost, 1)
        health = "healthy" if profit > 0 else "building" if runway >= 3 else "risk"
        state = {
            "cash": cash,
            "monthly_cost": monthly_cost,
            "monthly_income": monthly_income,
            "profit": profit,
            "runway": runway,
            "business_health": health,
            "updated_at": _now(),
        }
        data.update(state)
        save_json_atomic(self.path, data)
        return state
