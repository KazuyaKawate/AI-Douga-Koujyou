from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.learning_engine.learning_models import now_iso, require_dry_run
from src.revenue_engine.revenue_models import RevenuePlan
from src.revenue_engine.task_importer import CommanderTaskImporter
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


REVENUE_PLAN_PATH = PROJECT_ROOT / "config" / "revenue_plan.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RevenuePlanner:
    def build_plan(self, ranked: list[dict[str, Any]]) -> dict[str, Any]:
        today = ranked[:1]
        week = ranked[:3]
        month = ranked[:5]
        quarter = ranked[:8]
        return {
            "plan_date": date.today().isoformat(),
            "today": self._actions(today, "today"),
            "week": self._actions(week, "week"),
            "month": self._actions(month, "month"),
            "quarter": self._actions(quarter, "quarter"),
            "mission_planner_payload": {
                "source": "revenue_engine",
                "status": "ready",
                "top_action": today[0] if today else {},
                "ranked_actions": ranked[:10],
                "created_at": _now(),
            },
            "created_at": _now(),
        }

    @staticmethod
    def _actions(items: list[dict[str, Any]], window: str) -> list[dict[str, Any]]:
        return [
            {
                "window": window,
                "opportunity_id": item.get("opportunity_id", ""),
                "title": item.get("title", ""),
                "channel": item.get("channel", ""),
                "revenue_score": item.get("revenue_score", 0),
                "expected_profit": item.get("expected_profit", 0),
                "roi": item.get("roi", 0),
                "next_action": item.get("next_action", ""),
            }
            for item in items
        ]


class CommanderRevenuePlanner:
    """Convert Commander pending tasks into local-only revenue plans."""

    def __init__(
        self,
        *,
        importer: CommanderTaskImporter | None = None,
        path: str | Path = REVENUE_PLAN_PATH,
    ) -> None:
        self.importer = importer or CommanderTaskImporter()
        self.path = Path(path)

    def build_from_commander_tasks(
        self,
        *,
        limit: int | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        require_dry_run(dry_run)
        tasks = self.importer.load_pending_tasks(limit=limit, dry_run=True)
        plans = [self.task_to_plan(task).to_dict() for task in tasks]
        plans = sorted(
            plans,
            key=lambda plan: (
                -self._priority_weight(str(plan.get("priority", "LOW"))),
                int(plan.get("estimated_first_profit_days", 9999)),
                int(plan.get("estimated_initial_cost", 999999)),
                -int(plan.get("confidence", 0)),
            ),
        )
        state = {
            "enabled": True,
            "source": "commander_learning_tasks",
            "plans": plans,
            "summary": {
                "task_count": len(tasks),
                "plan_count": len(plans),
                "top_plan_id": plans[0]["plan_id"] if plans else "",
                "status": "planned",
                "review_required": True,
                "dry_run": True,
                "local_first": True,
                "external_api_enabled": False,
                "production_actions_enabled": False,
                "updated_at": now_iso(),
            },
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "updated_at": now_iso(),
        }
        save_json_atomic(self.path, state)
        return state

    def load_plan_state(self) -> dict[str, Any]:
        data = load_json(self.path, default={})
        return dict(data) if isinstance(data, dict) else {}

    def task_to_plan(self, task: dict[str, Any]) -> RevenuePlan:
        category = self.classify_revenue(task)
        days = int(task.get("estimated_profit_days", 30) or 30)
        cost = int(task.get("estimated_initial_cost", 0) or 0)
        confidence = int(task.get("confidence", 50) or 50)
        automation = int(task.get("automation_ratio", 0) or 0)
        manual = int(task.get("manual_ratio", 100) or 100)
        expected_profit = self.estimate_expected_profit(category, days, cost, confidence)
        return RevenuePlan(
            task_id=str(task.get("task_id", "")),
            title=str(task.get("title", "")),
            expected_profit=expected_profit,
            estimated_first_profit_days=days,
            estimated_monthly_profit=self.estimate_monthly_profit(expected_profit, days),
            estimated_initial_cost=cost,
            difficulty=self.estimate_difficulty(days, cost, manual, list(task.get("risk", []) or [])),
            automation_ratio=automation,
            manual_ratio=manual,
            required_engines=self.required_engines(category),
            required_review=True,
            business_category=category,
            priority=str(task.get("priority", "MEDIUM")),
            confidence=confidence,
            risk=list(task.get("risk", []) or []),
            source=dict(task.get("source", {}) or {}),
            dry_run=True,
        )

    def classify_revenue(self, task: dict[str, Any]) -> str:
        text = " ".join(
            [
                str(task.get("title", "")),
                str(task.get("description", "")),
                str(task.get("business_category", "")),
                str(task.get("recommended_phase", "")),
            ]
        ).lower()
        if "threads" in text:
            return "Threads"
        if "website" in text or "official site" in text:
            return "Website"
        if "affiliate" in text:
            return "Affiliate"
        if "consult" in text or "lead" in text:
            return "Consulting"
        if "note" in text:
            return "note"
        return "Other"

    def estimate_expected_profit(self, category: str, days: int, cost: int, confidence: int) -> int:
        base = {
            "note": 5000,
            "Threads": 3500,
            "Website": 8000,
            "Affiliate": 7000,
            "Consulting": 15000,
            "Other": 2500,
        }.get(category, 2500)
        speed_bonus = max(0, 45 - days) * 80
        confidence_bonus = confidence * 40
        return max(0, int(base + speed_bonus + confidence_bonus - cost * 0.2))

    @staticmethod
    def estimate_monthly_profit(expected_profit: int, days: int) -> int:
        multiplier = 3 if days <= 14 else 2 if days <= 30 else 1
        return max(0, int(expected_profit * multiplier))

    @staticmethod
    def estimate_difficulty(days: int, cost: int, manual_ratio: int, risks: list[str]) -> str:
        score = 0
        if days > 30:
            score += 1
        if cost >= 5000:
            score += 1
        if manual_ratio >= 85:
            score += 1
        if len(risks) >= 2:
            score += 1
        if score >= 3:
            return "Hard"
        if score == 0:
            return "Easy"
        return "Medium"

    @staticmethod
    def required_engines(category: str) -> list[str]:
        engines = ["revenue_engine"]
        if category == "note":
            engines.append("note")
        elif category == "Threads":
            engines.append("threads")
        elif category == "Website":
            engines.append("website")
        elif category == "Affiliate":
            engines.extend(["note", "affiliate"])
        elif category == "Consulting":
            engines.append("commander")
        return engines

    @staticmethod
    def _priority_weight(priority: str) -> int:
        normalized = priority.strip().upper()
        return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(normalized, 0)
