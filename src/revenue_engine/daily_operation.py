from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.revenue_engine.threads_draft_flow import RevenueThreadsDraftFlow
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic


REPORT_DIR = PROJECT_ROOT / "reports" / "revenue_daily"
logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RevenueDailyOperationMode:
    def __init__(
        self,
        *,
        dashboard: RevenueEngineDashboard | None = None,
        threads_flow: RevenueThreadsDraftFlow | None = None,
        report_dir: str | Path = REPORT_DIR,
    ) -> None:
        self.dashboard = dashboard or RevenueEngineDashboard()
        self.threads_flow = threads_flow or RevenueThreadsDraftFlow(dashboard=self.dashboard)
        self.report_dir = Path(report_dir)

    def run_once(self, *, theme: str | None = None, dry_run: bool = True) -> dict[str, Any]:
        if not dry_run:
            logger.error("Daily revenue operation only supports DryRun.")
            return {"status": "failed", "stage": "dry_run_guard", "error": "Daily operation requires dry_run=True.", "dry_run": False}

        operation_id = f"daily-{uuid4().hex[:10]}"
        content = self.threads_flow.run(theme=theme, dry_run=True)
        if content.get("status") != "success":
            logger.error("Daily revenue operation failed at content generation: %s", content.get("stage", "unknown"))
            return {
                "status": "failed",
                "stage": "content_generation",
                "operation_id": operation_id,
                "content_result": content,
                "dry_run": True,
            }

        report_text = self.build_report(operation_id, content)
        report_path = self.export_report(report_text)
        dashboard_record = self.record_daily_operation(operation_id, content, report_path)
        return {
            "status": "success",
            "operation_id": operation_id,
            "theme": content.get("note_result", {}).get("theme", ""),
            "note_result": content.get("note_result", {}),
            "threads_post": content.get("threads_post", {}),
            "dashboard_record": dashboard_record,
            "report_path": str(report_path),
            "dry_run": True,
        }

    def build_report(self, operation_id: str, content: dict[str, Any]) -> str:
        note = content.get("note_result", {})
        article = note.get("article", {})
        threads = content.get("threads_post", {})
        return (
            f"# AIOS Revenue Daily Report\n\n"
            f"- Operation ID: {operation_id}\n"
            f"- Date: {date.today().isoformat()}\n"
            f"- DryRun: True\n"
            f"- Theme: {note.get('theme', '')}\n"
            f"- note Title: {article.get('title', '')}\n"
            f"- note Draft URL: {note.get('save_url', '')}\n"
            f"- Threads Waiting: True\n\n"
            f"## Threads Post\n\n"
            f"{threads.get('text', '')}\n\n"
            f"## Status\n\n"
            f"今日のコンテンツ一式はDryRunで生成され、Dashboardの公開待ちに登録されました。\n"
        )

    def export_report(self, content: str) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        path = self.report_dir / f"{date.today().isoformat()}_revenue_daily_report.md"
        path.write_text(content, encoding="utf-8")
        return path

    def record_daily_operation(self, operation_id: str, content: dict[str, Any], report_path: Path) -> dict[str, Any]:
        note = content.get("note_result", {})
        record = {
            "operation_id": operation_id,
            "status": "completed",
            "dry_run": True,
            "theme": note.get("theme", ""),
            "note_save_url": note.get("save_url", ""),
            "threads_waiting_id": content.get("dashboard_record", {}).get("waiting_id", ""),
            "report_path": str(report_path),
            "created_at": _now(),
        }
        state = self.dashboard.load_state()
        state.setdefault("daily_operation_runs", []).insert(0, record)
        state["daily_operation_runs"] = state["daily_operation_runs"][:100]
        state["last_daily_operation"] = record
        self.dashboard.save_state(state)
        return record
