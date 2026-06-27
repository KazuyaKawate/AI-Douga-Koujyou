"""sync_models — Data models for Google Workspace Sync (v5.2)."""
from __future__ import annotations
from typing import TypedDict

SYNC_STATUSES = ["pending", "in_progress", "success", "failed", "dry_run", "conflict"]
CONFLICT_LEVELS = ["none", "warning", "error"]

STATUS_ICONS = {
    "pending":     "⏳",
    "in_progress": "🔄",
    "success":     "✅",
    "failed":      "❌",
    "dry_run":     "🔍",
    "conflict":    "⚠️",
}

CONNECTION_ICONS = {
    "unconfigured":   "⚫",
    "no_credentials": "🔴",
    "no_spreadsheet": "🟡",
    "disabled":       "⚪",
    "configured":     "🟡",
    "connected":      "🟢",
}


class SyncTarget(TypedDict, total=False):
    target_id:    str
    name:         str
    local_file:   str
    sheet_name:   str
    enabled:      bool
    last_synced:  str | None


class SyncRecord(TypedDict, total=False):
    record_id:   str
    timestamp:   str
    target_id:   str
    status:      str       # success | failed | dry_run | conflict
    dry_run:     bool
    rows_synced: int
    conflicts:   int
    changes:     int
    error:       str | None
    duration_ms: int


class SyncPreview(TypedDict, total=False):
    target_id:      str
    target_name:    str
    sheet_name:     str
    local_file:     str
    rows_total:     int
    rows_changed:   int
    rows_new:       int
    rows_deleted:   int
    conflict_count: int
    conflicts:      list[dict]
    ready:          bool
    error:          str | None


class SyncConflict(TypedDict, total=False):
    target_id:    str
    field:        str
    local_value:  str
    remote_value: str
    severity:     str    # warning | error
    description:  str


def make_sync_record(
    target_id: str,
    status: str,
    dry_run: bool = True,
    rows_synced: int = 0,
    conflicts: int = 0,
    changes: int = 0,
    error: str | None = None,
    duration_ms: int = 0,
) -> dict:
    import uuid
    from datetime import datetime
    return {
        "record_id":   f"sync_{uuid.uuid4().hex[:8]}",
        "timestamp":   datetime.now().isoformat(timespec="seconds"),
        "target_id":   target_id,
        "status":      status,
        "dry_run":     dry_run,
        "rows_synced": rows_synced,
        "conflicts":   conflicts,
        "changes":     changes,
        "error":       error,
        "duration_ms": duration_ms,
    }
