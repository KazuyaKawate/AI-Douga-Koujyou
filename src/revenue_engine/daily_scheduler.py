from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.revenue_engine.daily_operation import RevenueDailyOperationMode
from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


LOG_PATH = PROJECT_ROOT / "logs" / "revenue_daily_scheduler.json"
logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RevenueDailyScheduler:
    def __init__(
        self,
        *,
        run_at: str = "09:00",
        dashboard: RevenueEngineDashboard | None = None,
        operation: RevenueDailyOperationMode | None = None,
        log_path: str | Path = LOG_PATH,
        poll_seconds: float = 60.0,
    ) -> None:
        self.run_at = run_at
        self.dashboard = dashboard or RevenueEngineDashboard()
        self.operation = operation or RevenueDailyOperationMode(dashboard=self.dashboard)
        self.log_path = Path(log_path)
        self.poll_seconds = max(float(poll_seconds), 0.1)
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def tick(self, *, now: datetime | None = None) -> dict[str, Any]:
        current = now or datetime.now()
        if not self.should_run(current):
            return self._record_scheduler_event("skipped", current, reason="not_due")
        return self.run_due_once(current)

    def run_due_once(self, now: datetime | None = None) -> dict[str, Any]:
        current = now or datetime.now()
        if self._is_locked():
            return self._record_scheduler_event("skipped", current, reason="already_running")
        if self._already_completed_today(current):
            return self._record_scheduler_event("skipped", current, reason="already_completed_today")

        schedule_id = f"rsched-{uuid4().hex[:10]}"
        self._set_lock(schedule_id, current)
        attempts: list[dict[str, Any]] = []
        try:
            for attempt in (1, 2):
                try:
                    result = self.operation.run_once(dry_run=True)
                except Exception as exc:
                    logger.exception("Revenue daily scheduler attempt failed.")
                    result = {"status": "failed", "error": str(exc), "dry_run": True}
                attempts.append({"attempt": attempt, "status": result.get("status", ""), "result": self._summarize_result(result)})
                if result.get("status") == "success":
                    return self._finish(schedule_id, current, "success", attempts, result)
            return self._finish(schedule_id, current, "failed", attempts, attempts[-1].get("result", {}))
        finally:
            self._clear_lock()

    def should_run(self, now: datetime) -> bool:
        hour, minute = self._run_at_parts()
        return (now.hour, now.minute) >= (hour, minute)

    def start(self) -> dict[str, Any]:
        if self._thread and self._thread.is_alive():
            return {"status": "already_running", "running": True}
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="RevenueDailyScheduler")
        self._thread.start()
        return {"status": "running", "running": True}

    def stop(self, timeout: float = 5.0) -> dict[str, Any]:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        return {"status": "stopped", "running": bool(self._thread and self._thread.is_alive())}

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self.tick()
            self._stop_event.wait(self.poll_seconds)

    def _run_at_parts(self) -> tuple[int, int]:
        try:
            hour, minute = self.run_at.split(":", 1)
            return max(0, min(23, int(hour))), max(0, min(59, int(minute)))
        except Exception:
            return 9, 0

    def _is_locked(self) -> bool:
        if self._running:
            return True
        state = self.dashboard.load_state()
        return state.get("daily_scheduler_lock", {}).get("status") == "running"

    def _set_lock(self, schedule_id: str, now: datetime) -> None:
        self._running = True
        state = self.dashboard.load_state()
        state["daily_scheduler_lock"] = {"status": "running", "schedule_id": schedule_id, "started_at": now.isoformat(timespec="seconds")}
        self.dashboard.save_state(state)

    def _clear_lock(self) -> None:
        self._running = False
        state = self.dashboard.load_state()
        state["daily_scheduler_lock"] = {"status": "idle", "updated_at": _now()}
        self.dashboard.save_state(state)

    def _already_completed_today(self, now: datetime) -> bool:
        today = now.date().isoformat()
        state = self.dashboard.load_state()
        for row in state.get("daily_scheduler_history", []):
            if row.get("status") == "success" and str(row.get("scheduled_date", "")) == today:
                return True
        return False

    def _finish(
        self,
        schedule_id: str,
        now: datetime,
        status: str,
        attempts: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        event = {
            "schedule_id": schedule_id,
            "status": status,
            "scheduled_date": now.date().isoformat(),
            "run_at": self.run_at,
            "dry_run": True,
            "attempts": attempts,
            "result": self._summarize_result(result),
            "created_at": _now(),
        }
        self._append_history(event)
        self._append_log(event)
        return event

    def _record_scheduler_event(self, status: str, now: datetime, *, reason: str) -> dict[str, Any]:
        event = {
            "schedule_id": f"rsched-{uuid4().hex[:10]}",
            "status": status,
            "reason": reason,
            "scheduled_date": now.date().isoformat(),
            "run_at": self.run_at,
            "dry_run": True,
            "created_at": _now(),
        }
        self._append_log(event)
        return event

    def _append_history(self, event: dict[str, Any]) -> None:
        state = self.dashboard.load_state()
        state.setdefault("daily_scheduler_history", []).insert(0, event)
        state["daily_scheduler_history"] = state["daily_scheduler_history"][:100]
        state["last_daily_scheduler_run"] = event
        self.dashboard.save_state(state)

    def _append_log(self, event: dict[str, Any]) -> None:
        data = load_json(self.log_path, default={})
        if not isinstance(data, dict):
            data = {}
        data.setdefault("events", []).insert(0, event)
        data["events"] = data["events"][:300]
        save_json_atomic(self.log_path, data)

    @staticmethod
    def _summarize_result(result: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": result.get("status", ""),
            "operation_id": result.get("operation_id", ""),
            "theme": result.get("theme", ""),
            "report_path": result.get("report_path", ""),
            "dry_run": bool(result.get("dry_run", True)),
            "error": result.get("error", ""),
        }
