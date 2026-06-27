"""Factory event bus — standard inter-factory event system."""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
EVENTS_PATH = ROOT / "config" / "factory_events.json"

MAX_EVENTS = 200

# ── Event type constants ───────────────────────────────────────────────────────

EVENT_FACTORY_INITIALIZED = "factory_initialized"
EVENT_FACTORY_COMPLETED   = "factory_completed"
EVENT_FACTORY_FAILED      = "factory_failed"
EVENT_FACTORY_UPDATED     = "factory_updated"
EVENT_PROJECT_UPDATED     = "project_updated"
EVENT_KPI_CHANGED         = "kpi_changed"
EVENT_REPORT_GENERATED    = "report_generated"

ALL_EVENTS = (
    EVENT_FACTORY_INITIALIZED,
    EVENT_FACTORY_COMPLETED,
    EVENT_FACTORY_FAILED,
    EVENT_FACTORY_UPDATED,
    EVENT_PROJECT_UPDATED,
    EVENT_KPI_CHANGED,
    EVENT_REPORT_GENERATED,
)

EVENT_LABELS: dict[str, str] = {
    EVENT_FACTORY_INITIALIZED: "工場初期化",
    EVENT_FACTORY_COMPLETED:   "工場完了",
    EVENT_FACTORY_FAILED:      "工場エラー",
    EVENT_FACTORY_UPDATED:     "工場更新",
    EVENT_PROJECT_UPDATED:     "プロジェクト更新",
    EVENT_KPI_CHANGED:         "KPI変更",
    EVENT_REPORT_GENERATED:    "レポート生成",
}


# ── Persistence ────────────────────────────────────────────────────────────────

def _default_store() -> dict:
    return {
        "events": [],
        "meta": {
            "version":    "4.5.1",
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "max_events": MAX_EVENTS,
        },
    }


def load_events() -> dict:
    if EVENTS_PATH.exists():
        try:
            return json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _default_store()


def _save_events(data: dict) -> None:
    EVENTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── EventBus ──────────────────────────────────────────────────────────────────

class EventBus:
    """Simple in-process + persistent event bus."""

    _subscribers: dict[str, list] = {}

    @classmethod
    def subscribe(cls, event_type: str, callback) -> None:
        cls._subscribers.setdefault(event_type, []).append(callback)

    @classmethod
    def emit(cls, event_type: str, factory_name: str, payload: dict | None = None) -> str:
        """Emit an event, persist it, and call subscribers. Returns event_id."""
        event_id = "evt_" + uuid.uuid4().hex[:8]
        record = {
            "event_id":    event_id,
            "event_type":  event_type,
            "factory_name": factory_name,
            "payload":     payload or {},
            "timestamp":   datetime.now().isoformat(timespec="seconds"),
        }

        try:
            data = load_events()
            data["events"].append(record)
            if len(data["events"]) > MAX_EVENTS:
                data["events"] = data["events"][-MAX_EVENTS:]
            _save_events(data)
        except Exception:
            pass

        for cb in cls._subscribers.get(event_type, []):
            try:
                cb(record)
            except Exception:
                pass

        return event_id

    @classmethod
    def get_history(cls, event_type: str | None = None, factory_name: str | None = None,
                    limit: int = 50) -> list[dict]:
        data = load_events()
        events = data.get("events", [])
        if event_type:
            events = [e for e in events if e["event_type"] == event_type]
        if factory_name:
            events = [e for e in events if e["factory_name"] == factory_name]
        return list(reversed(events[-limit:]))

    @classmethod
    def get_summary(cls) -> dict:
        data = load_events()
        events = data.get("events", [])
        counts: dict[str, int] = {}
        for e in events:
            counts[e["event_type"]] = counts.get(e["event_type"], 0) + 1
        latest = events[-1]["timestamp"] if events else "—"
        return {
            "total":   len(events),
            "by_type": counts,
            "latest":  latest,
        }
