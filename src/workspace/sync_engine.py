"""sync_engine — Sync orchestration for Google Workspace Sync (v5.2 Phase 2).

All operations:
  - Dry-run by default (dry_run=True).
  - Never executed automatically.
  - Only triggered by explicit user action (manual button click).
  - Phase 1: no external API calls.
  - Phase 2: google_auth / sheet_reader / sheet_writer / sheet_diff / sync_executor added.
             Actual Sheets writes remain Phase 3+ (gspread integration).
"""
from __future__ import annotations
import time

from src.workspace.sheets_sync import prepare_mapping, read_local_data
from src.workspace.sync_history import log_sync
from src.workspace.sync_validator import load_settings, get_enabled_targets


def detect_changes(target_id: str, local_file: str) -> dict:
    """Read local JSON and compute change summary. Read-only. No API calls.

    Phase 1: treats all rows as new (no remote state cached yet).
    Phase 2+: will compare against last-synced remote snapshot.
    """
    rows, error = read_local_data(local_file)
    if error:
        return {"target_id": target_id, "rows_total": 0, "rows_changed": 0,
                "rows_new": 0, "rows_deleted": 0, "changes": 0,
                "error": error, "ready": False}
    return {
        "target_id":    target_id,
        "rows_total":   len(rows),
        "rows_changed": 0,
        "rows_new":     len(rows),
        "rows_deleted": 0,
        "changes":      len(rows),
        "error":        None,
        "ready":        True,
    }


def detect_conflicts(target_id: str, local_file: str) -> list[dict]:
    """Detect conflicts between local and remote state.

    Phase 1: always returns empty (no remote state available).
    Phase 2+: will compare against cached Sheet values.
    """
    return []


def generate_preview(settings: dict | None = None) -> list[dict]:
    """Generate sync preview for all enabled targets. Read-only. No API calls."""
    if settings is None:
        settings = load_settings()
    previews = []
    for t in get_enabled_targets(settings):
        target_id  = t.get("target_id", "")
        local_file = t.get("local_file", "")
        sheet_name = t.get("sheet_name", "")

        change_info = detect_changes(target_id, local_file)
        conflicts   = detect_conflicts(target_id, local_file)
        mapping     = prepare_mapping(target_id, local_file)

        previews.append({
            "target_id":      target_id,
            "target_name":    t.get("name", target_id),
            "sheet_name":     sheet_name or mapping.get("sheet_name", ""),
            "local_file":     local_file,
            "rows_total":     change_info["rows_total"],
            "rows_changed":   change_info.get("rows_changed", 0),
            "rows_new":       change_info.get("rows_new", 0),
            "rows_deleted":   change_info.get("rows_deleted", 0),
            "changes":        change_info["changes"],
            "conflicts":      conflicts,
            "conflict_count": len(conflicts),
            "ready":          change_info["ready"] and not change_info.get("error"),
            "error":          change_info.get("error"),
        })
    return previews


def run_dry_run(settings: dict | None = None) -> dict:
    """Simulate a full sync pass. Reads local data only. Logs the result."""
    if settings is None:
        settings = load_settings()

    t0 = time.time()
    previews = generate_preview(settings)
    duration_ms = int((time.time() - t0) * 1000)

    total_rows      = sum(p["rows_total"] for p in previews)
    total_changes   = sum(p["changes"] for p in previews)
    total_conflicts = sum(p["conflict_count"] for p in previews)

    log_sync(
        target_id="all",
        status="dry_run",
        dry_run=True,
        rows_synced=total_rows,
        conflicts=total_conflicts,
        changes=total_changes,
        duration_ms=duration_ms,
    )

    return {
        "dry_run":         True,
        "targets":         len(previews),
        "total_rows":      total_rows,
        "total_changes":   total_changes,
        "total_conflicts": total_conflicts,
        "duration_ms":     duration_ms,
        "previews":        previews,
        "executed":        False,
    }


def run_sync(settings: dict | None = None) -> dict:
    """Execute synchronization.

    Phase 1: always falls back to dry_run (no Google credentials available).
    Phase 2+: will perform actual Sheets writes when credentials are present
              and dry_run=False is explicitly set.
    """
    if settings is None:
        settings = load_settings()
    # Phase 1 guard: never execute real writes
    return run_dry_run(settings)


def get_sync_health(settings: dict | None = None) -> dict:
    """Return sync health summary. Read-only. Safe for AI CEO / dashboard integration."""
    from src.workspace.sync_history import get_summary
    from src.workspace.sync_validator import get_connection_status

    if settings is None:
        settings = load_settings()

    hist    = get_summary()
    conn    = get_connection_status(settings)
    targets = get_enabled_targets(settings)

    # Phase 2: include connector health if available
    connector_health: dict = {}
    try:
        from src.workspace.sync_executor import get_connector_health
        connector_health = get_connector_health(settings)
    except Exception:
        pass

    return {
        "available":         bool(settings),
        "connection_status": conn["status"],
        "connection_icon":   conn["icon"],
        "enabled":           conn["enabled"],
        "dry_run_default":   settings.get("dry_run_default", True),
        "last_sync":         hist["last_sync"],
        "last_status":       hist["last_status"],
        "total_syncs":       hist["total_syncs"],
        "total_conflicts":   hist["total_conflicts"],
        "pending_targets":   len(targets),
        "connector":         connector_health,
    }
