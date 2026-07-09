from __future__ import annotations

from datetime import datetime

from src.revenue_engine.daily_scheduler import RevenueDailyScheduler
from src.revenue_engine.dashboard import RevenueEngineDashboard


class SuccessfulOperation:
    def __init__(self) -> None:
        self.calls = 0

    def run_once(self, *, dry_run=True):
        self.calls += 1
        return {
            "status": "success",
            "operation_id": f"op-{self.calls}",
            "theme": "Scheduler Theme",
            "report_path": "reports/daily.md",
            "dry_run": dry_run,
        }


class FlakyOperation:
    def __init__(self) -> None:
        self.calls = 0

    def run_once(self, *, dry_run=True):
        self.calls += 1
        if self.calls == 1:
            return {"status": "failed", "error": "temporary", "dry_run": dry_run}
        return {"status": "success", "operation_id": "op-retry", "theme": "Retry Theme", "dry_run": dry_run}


def test_phase7_scheduler_runs_due_daily_operation_and_records_dashboard_history(tmp_path) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    operation = SuccessfulOperation()
    scheduler = RevenueDailyScheduler(
        run_at="09:00",
        dashboard=dashboard,
        operation=operation,
        log_path=tmp_path / "scheduler_log.json",
    )

    result = scheduler.tick(now=datetime(2026, 7, 9, 9, 0))
    state = dashboard.load_state()

    assert result["status"] == "success"
    assert operation.calls == 1
    assert result["dry_run"] is True
    assert state["daily_scheduler_history"][0]["schedule_id"] == result["schedule_id"]
    assert state["daily_scheduler_history"][0]["result"]["operation_id"] == "op-1"
    assert state["daily_scheduler_lock"]["status"] == "idle"


def test_phase7_scheduler_skips_before_time_and_blocks_duplicate_same_day(tmp_path) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    operation = SuccessfulOperation()
    scheduler = RevenueDailyScheduler(
        run_at="09:00",
        dashboard=dashboard,
        operation=operation,
        log_path=tmp_path / "scheduler_log.json",
    )

    before = scheduler.tick(now=datetime(2026, 7, 9, 8, 59))
    first = scheduler.tick(now=datetime(2026, 7, 9, 9, 0))
    duplicate = scheduler.tick(now=datetime(2026, 7, 9, 12, 0))

    assert before["status"] == "skipped"
    assert before["reason"] == "not_due"
    assert first["status"] == "success"
    assert duplicate["status"] == "skipped"
    assert duplicate["reason"] == "already_completed_today"
    assert operation.calls == 1


def test_phase7_scheduler_retries_once_and_saves_log(tmp_path) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    operation = FlakyOperation()
    log_path = tmp_path / "scheduler_log.json"
    scheduler = RevenueDailyScheduler(
        run_at="09:00",
        dashboard=dashboard,
        operation=operation,
        log_path=log_path,
    )

    result = scheduler.tick(now=datetime(2026, 7, 9, 9, 0))
    log_text = log_path.read_text(encoding="utf-8")

    assert result["status"] == "success"
    assert operation.calls == 2
    assert [row["status"] for row in result["attempts"]] == ["failed", "success"]
    assert "temporary" in log_text


def test_phase7_scheduler_prevents_double_start_when_lock_is_running(tmp_path) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    state = dashboard.load_state()
    state["daily_scheduler_lock"] = {"status": "running", "schedule_id": "existing"}
    dashboard.save_state(state)
    operation = SuccessfulOperation()
    scheduler = RevenueDailyScheduler(
        run_at="09:00",
        dashboard=dashboard,
        operation=operation,
        log_path=tmp_path / "scheduler_log.json",
    )

    result = scheduler.tick(now=datetime(2026, 7, 9, 9, 0))

    assert result["status"] == "skipped"
    assert result["reason"] == "already_running"
    assert operation.calls == 0
