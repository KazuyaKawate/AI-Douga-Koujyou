from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


REVENUE_SOURCES = ("note", "Threads", "Website", "Affiliate", "Ad", "API", "Service")
GROWTH_METRICS = ("traffic", "cv", "cvr", "ctr", "followers", "sales", "growth")
EMPLOYEES = ("Writer", "Developer", "Reviewer", "SEO", "Marketing", "Business")
SELF_COMPANY_CYCLE = ("plan", "implement", "review", "publish", "analyze", "improve")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class AutonomousCompanyEngine:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root)
        self.config = self.root / "config"

    def revenue_engine(self, business_queue: list[dict[str, Any]]) -> dict[str, Any]:
        sources = {source: {"expected_income": 0, "roi": 0, "tasks": 0} for source in REVENUE_SOURCES}
        for job in business_queue:
            task = job.get("business_task", {})
            source = self._source(task.get("categories", []))
            bucket = sources[source]
            bucket["expected_income"] += int(task.get("expected_income", 0) or 0)
            bucket["roi"] = max(float(bucket["roi"]), float(task.get("roi", 0) or 0))
            bucket["tasks"] += 1
        state = {"sources": sources, "updated_at": _now()}
        save_json_atomic(self.config / "commander_revenue_engine.json", state)
        return state

    def growth_engine(self) -> dict[str, Any]:
        data = load_json(self.config / "commander_growth_engine.json", default={}) or {}
        today = date.today().isoformat()
        snapshot = {metric: float(data.get(metric, 0) or 0) for metric in GROWTH_METRICS}
        snapshot.update({"date": today, "updated_at": _now()})
        data.update(snapshot)
        data.setdefault("history", []).insert(0, snapshot)
        data["history"] = data["history"][:90]
        save_json_atomic(self.config / "commander_growth_engine.json", data)
        return snapshot

    def employee_queues(self, business_queue: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        queues = {employee: [] for employee in EMPLOYEES}
        for job in business_queue:
            role = self._employee(job.get("business_task", {}).get("categories", []))
            queues[role].append({"job_id": job.get("job_id", ""), "title": job.get("instruction", ""), "status": job.get("status", "")})
        save_json_atomic(self.config / "commander_employees.json", {"queues": queues, "updated_at": _now()})
        return queues

    def meeting_reports(self, summary: dict[str, Any]) -> dict[str, Any]:
        reports = {
            "date": date.today().isoformat(),
            "morning_report": f"Today's Mission: {len(summary.get('dashboard', {}).get('today', []))} revenue tasks.",
            "night_report": f"Completed: {summary.get('history_metrics', {}).get('completed_count', 0)}.",
            "revenue_report": f"Forecast: {summary.get('revenue_plan', {}).get('queue_forecast', 0)}.",
            "risk_report": f"System Health: {summary.get('system_health', {}).get('status', 'ok')}.",
            "updated_at": _now(),
        }
        save_json_atomic(self.config / "commander_ceo_meeting.json", reports)
        return reports

    def self_company_cycle(self) -> dict[str, Any]:
        state = {"cycle": list(SELF_COMPANY_CYCLE), "knowledge_learning": True, "updated_at": _now()}
        save_json_atomic(self.config / "commander_self_company.json", state)
        return state

    @staticmethod
    def _source(categories: list[str]) -> str:
        if "note" in categories:
            return "note"
        if "threads" in categories:
            return "Threads"
        if "website" in categories or "seo" in categories:
            return "Website"
        if "affiliate" in categories:
            return "Affiliate"
        return "Service"

    @staticmethod
    def _employee(categories: list[str]) -> str:
        if "note" in categories:
            return "Writer"
        if "website" in categories or "seo" in categories:
            return "SEO"
        if "threads" in categories or "affiliate" in categories:
            return "Marketing"
        if "development" in categories or "coding" in categories or "commander" in categories:
            return "Developer"
        if "maintenance" in categories or "release" in categories:
            return "Reviewer"
        return "Business"
