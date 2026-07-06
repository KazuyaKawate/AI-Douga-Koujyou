from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from src.business_engine.manager import BusinessEngineStore
from src.business_engine.worker import BusinessWorker


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_scheduler_state() -> dict[str, Any]:
    return {
        "enabled": False,
        "status": "stopped",
        "interval_seconds": 300,
        "heartbeat_at": "",
        "last_tick_at": "",
        "last_result": "Scheduler disabled by default.",
    }


class SchedulerDaemon:
    """Optional local scheduler controller.

    This is intentionally disabled by default and only runs local queued jobs
    through BusinessWorker. It never calls publishing, affiliate, SEO, or paid
    provider APIs.
    """

    def __init__(self, store: BusinessEngineStore | None = None) -> None:
        self.store = store or BusinessEngineStore()

    def state(self) -> dict[str, Any]:
        data = self.store.load()
        state = data.setdefault("scheduler_daemon", default_scheduler_state())
        for key, value in default_scheduler_state().items():
            state.setdefault(key, value)
        return state

    def configure(self, interval_seconds: int) -> dict[str, Any]:
        data = self.store.load()
        state = data.setdefault("scheduler_daemon", default_scheduler_state())
        state["interval_seconds"] = max(int(interval_seconds or 60), 60)
        state["last_result"] = "Scheduler interval updated."
        self.store.save(data)
        return state

    def start(self) -> dict[str, Any]:
        data = self.store.load()
        state = data.setdefault("scheduler_daemon", default_scheduler_state())
        state.update({
            "enabled": True,
            "status": "running",
            "heartbeat_at": _now(),
            "last_result": "Scheduler started in local-only mode.",
        })
        self.store.save(data)
        return state

    def stop(self) -> dict[str, Any]:
        data = self.store.load()
        state = data.setdefault("scheduler_daemon", default_scheduler_state())
        state.update({
            "enabled": False,
            "status": "stopped",
            "heartbeat_at": _now(),
            "last_result": "Scheduler stopped.",
        })
        self.store.save(data)
        return state

    def heartbeat(self) -> dict[str, Any]:
        data = self.store.load()
        state = data.setdefault("scheduler_daemon", default_scheduler_state())
        state["heartbeat_at"] = _now()
        if not state.get("enabled"):
            state["status"] = "stopped"
        self.store.save(data)
        return state

    def tick(self, *, force: bool = False) -> dict[str, Any]:
        data = self.store.load()
        state = data.setdefault("scheduler_daemon", default_scheduler_state())
        if not state.get("enabled"):
            state.update({
                "status": "stopped",
                "heartbeat_at": _now(),
                "last_result": "Scheduler disabled; no job executed.",
            })
            self.store.save(data)
            return state

        now = datetime.now()
        last_tick = _parse_time(state.get("last_tick_at", ""))
        interval = max(int(state.get("interval_seconds", 300)), 60)
        if not force and last_tick and now < last_tick + timedelta(seconds=interval):
            state.update({
                "status": "running",
                "heartbeat_at": _now(),
                "last_result": "Waiting for next interval.",
            })
            self.store.save(data)
            return state

        result = BusinessWorker(self.store).execute_next(auto_retry=False)
        data = self.store.load()
        state = data.setdefault("scheduler_daemon", default_scheduler_state())
        state.update({
            "status": "running",
            "heartbeat_at": _now(),
            "last_tick_at": _now(),
            "last_result": result.message if result else "No queued jobs.",
        })
        self.store.save(data)
        return state


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
