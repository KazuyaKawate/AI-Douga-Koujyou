"""sync_history — Sync history logging for Google Workspace Sync (v5.2)."""
from __future__ import annotations
import json
from pathlib import Path

from src.workspace.sync_models import make_sync_record

ROOT = Path(__file__).parent.parent.parent
HISTORY_PATH = ROOT / "config" / "sync_history.json"
MAX_HISTORY = 100


def _default() -> dict:
    return {
        "meta":    {"version": "5.2", "module": "workspace-sync"},
        "history": [],
    }


def load_history() -> dict:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _default()


def save_history(data: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def log_sync(
    target_id: str,
    status: str,
    dry_run: bool = True,
    rows_synced: int = 0,
    conflicts: int = 0,
    changes: int = 0,
    error: str | None = None,
    duration_ms: int = 0,
) -> dict:
    """Append a sync record to history. Returns the created record."""
    record = make_sync_record(
        target_id=target_id,
        status=status,
        dry_run=dry_run,
        rows_synced=rows_synced,
        conflicts=conflicts,
        changes=changes,
        error=error,
        duration_ms=duration_ms,
    )
    data = load_history()
    data.setdefault("history", []).insert(0, record)
    if len(data["history"]) > MAX_HISTORY:
        data["history"] = data["history"][:MAX_HISTORY]
    save_history(data)
    return record


def get_last_sync() -> dict | None:
    history = load_history().get("history", [])
    return history[0] if history else None


def get_summary() -> dict:
    data = load_history()
    history = data.get("history", [])
    last = history[0] if history else None
    approved = [r for r in history if r.get("status") == "success"]
    failed = [r for r in history if r.get("status") == "failed"]
    return {
        "total_syncs":     len(history),
        "successful":      len(approved),
        "failed":          len(failed),
        "total_conflicts": sum(r.get("conflicts", 0) for r in history),
        "last_sync":       last.get("timestamp", "—") if last else "—",
        "last_status":     last.get("status", "—") if last else "—",
        "last_dry_run":    last.get("dry_run", True) if last else True,
    }


def get_recent(n: int = 10) -> list[dict]:
    return load_history().get("history", [])[:n]


def clear_history() -> None:
    save_history(_default())
