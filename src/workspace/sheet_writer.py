"""sheet_writer — Google Sheets write abstraction for Creator Factory OS (v5.2 Phase 3).

TRIPLE-LOCK WRITE GUARD (all three must be true to write):
  1. auth_mode != 'disabled'
  2. dry_run == False
  3. manual_execute == True

ADDITIONAL GUARDS (Phase 3):
  4. gspread installed
  5. google-auth installed
  6. credential file exists

Default behavior is always preview-only. Never crashes UI. Never writes by accident.
Actual writes are Phase 4+ (live gspread call).
"""
from __future__ import annotations

from src.workspace.google_auth import get_auth_config, get_credential_status, get_dependency_status


def _can_write(auth_mode: str, dry_run: bool, manual_execute: bool) -> tuple[bool, str]:
    """Triple-lock write guard. All three conditions must be met to allow writes."""
    if auth_mode == "disabled":
        return False, "auth_mode が 'disabled' のため書き込み不可"
    if dry_run:
        return False, "dry_run=True のため書き込み不可（プレビューのみ）"
    if not manual_execute:
        return False, "manual_execute=False のため書き込み不可（手動承認が必要）"
    return True, "書き込み条件を満たしています（Phase 3+で実装予定）"


def write_rows(
    sheet_name: str,
    rows: list[dict],
    *,
    dry_run: bool = True,
    manual_execute: bool = False,
    settings: dict | None = None,
) -> dict:
    """Write rows to a Google Sheet.

    Default: preview-only (dry_run=True, manual_execute=False).
    Actual write: requires dry_run=False AND manual_execute=True AND auth_mode != 'disabled'.
    Phase 3+: will call gspread when all three guards pass.
    """
    auth_cfg = get_auth_config(settings)
    auth_mode = auth_cfg["auth_mode"]
    can_write, reason = _can_write(auth_mode, dry_run, manual_execute)

    base = {
        "executed":       False,
        "dry_run":        dry_run,
        "manual_execute": manual_execute,
        "auth_mode":      auth_mode,
        "sheet_name":     sheet_name,
        "rows_preview":   len(rows),
        "rows_written":   0,
        "reason":         reason,
        "preview":        [_row_preview(r) for r in rows[:5]],
    }

    if not can_write:
        return base

    # Dependency guard — must be checked before credential and API access
    deps = get_dependency_status()
    if not deps["all_ready"]:
        missing = ", ".join(deps["missing"])
        base["reason"] = f"依存パッケージが不足しています: {missing} → {deps['install_hint']}"
        return base

    cred = get_credential_status(settings)
    if not cred["ready"]:
        base["reason"] = f"認証エラー: {cred['label']}"
        return base

    # Phase 4+: actual gspread write goes here.
    base["reason"] = "Phase 4+ で gspread 実装予定（現在: Phase 3 準備完了）"
    return base


def _row_preview(row: dict) -> dict:
    """Truncate row values for safe display in preview."""
    return {k: str(v)[:50] for k, v in list(row.items())[:8]}


def get_writer_status(settings: dict | None = None) -> dict:
    """Return writer configuration status. No side effects."""
    auth_cfg = get_auth_config(settings)
    return {
        "auth_mode":     auth_cfg["auth_mode"],
        "write_enabled": auth_cfg["auth_mode"] != "disabled",
        "phase":         "Phase 3 (preview-only, gspread ready)",
        "note":          "Actual writes require Phase 4+ gspread live integration",
    }
