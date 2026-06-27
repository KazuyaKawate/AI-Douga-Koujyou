"""approval_queue — Approval queue manager for Creator Factory OS v5.1.

Stores pending/reviewed actions in config/approval_queue.json.
Aggregates items from AI CEO, Automation Factory, Development Studio, and manual input.
Never executes actions.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

from src.approval.approval_models import make_item, STATUSES, is_pending

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "approval_queue.json"
MAX_HISTORY = 100


def _default_store() -> dict:
    return {
        "meta": {"version": "5.1", "created_at": datetime.now().isoformat(timespec="seconds")},
        "pending": [],
        "history": [],
    }


def load_queue() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _default_store()


def save_queue(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_pending() -> list[dict]:
    data = load_queue()
    return [item for item in data.get("pending", []) if item.get("status") == "pending"]


def get_all_pending_raw() -> list[dict]:
    return load_queue().get("pending", [])


def get_history(limit: int = 50) -> list[dict]:
    return load_queue().get("history", [])[:limit]


def add_item(
    title: str,
    source: str,
    command_summary: str,
    expected_impact: str,
    estimated_risk: str = "low",
    affected_files: list[str] | None = None,
    related_id: str = "",
    notes: str = "",
) -> dict:
    """Add a new pending item to the queue. Returns the created item."""
    item = make_item(
        title=title,
        source=source,
        command_summary=command_summary,
        expected_impact=expected_impact,
        estimated_risk=estimated_risk,
        affected_files=affected_files,
        related_id=related_id,
        notes=notes,
    )
    data = load_queue()
    data.setdefault("pending", []).insert(0, item)
    save_queue(data)
    return item


def _update_item_status(approval_id: str, status: str, notes: str = "") -> dict | None:
    """Internal: move an item from pending to history with new status."""
    data = load_queue()
    pending = data.get("pending", [])
    target = next((i for i in pending if i.get("approval_id") == approval_id), None)
    if not target:
        return None

    target["status"] = status
    target["reviewed_at"] = datetime.now().isoformat(timespec="seconds")
    if notes:
        target["notes"] = notes

    data["pending"] = [i for i in pending if i.get("approval_id") != approval_id]
    history = data.setdefault("history", [])
    history.insert(0, target)
    if len(history) > MAX_HISTORY:
        data["history"] = history[:MAX_HISTORY]

    save_queue(data)
    return target


def approve_item(approval_id: str, notes: str = "") -> dict | None:
    return _update_item_status(approval_id, "approved", notes)


def reject_item(approval_id: str, notes: str = "") -> dict | None:
    return _update_item_status(approval_id, "rejected", notes)


def expire_item(approval_id: str) -> dict | None:
    return _update_item_status(approval_id, "expired")


def delete_pending(approval_id: str) -> bool:
    data = load_queue()
    before = len(data.get("pending", []))
    data["pending"] = [i for i in data.get("pending", []) if i.get("approval_id") != approval_id]
    if len(data["pending"]) < before:
        save_queue(data)
        return True
    return False


def get_summary() -> dict:
    data = load_queue()
    pending = [i for i in data.get("pending", []) if i.get("status") == "pending"]
    history = data.get("history", [])
    approved = [i for i in history if i.get("status") == "approved"]
    rejected = [i for i in history if i.get("status") == "rejected"]
    high_risk = [i for i in pending if i.get("estimated_risk") == "high"]
    return {
        "pending_count":  len(pending),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "high_risk_count": len(high_risk),
        "total_reviewed": len(history),
    }
