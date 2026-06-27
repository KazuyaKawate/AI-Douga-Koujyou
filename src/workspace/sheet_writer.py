"""sheet_writer — Google Sheets write abstraction for Creator Factory OS (v5.2 Phase 4-1).

QUAD-LOCK WRITE GUARD (all four must be true to write):
  1. auth_mode != 'disabled'
  2. dry_run == False
  3. manual_execute == True
  4. allow_write == True   ← Phase 4-1: always False by default; Phase 4-2+ enables writes

DEPENDENCY GUARDS (checked after quad-lock):
  5. gspread installed
  6. google-auth installed
  7. credential file exists

Default behavior is always preview-only. Never crashes UI. Never writes by accident.
Actual writes remain Phase 4-2+ (Phase 4-1 = read-only connection test only).
"""
from __future__ import annotations

from src.workspace.google_auth import get_auth_config, get_credential_status, get_dependency_status


def _can_write(
    auth_mode: str,
    dry_run: bool,
    manual_execute: bool,
    allow_write: bool = False,
) -> tuple[bool, str]:
    """Quad-lock write guard. All four conditions must be met to allow writes."""
    if auth_mode == "disabled":
        return False, "auth_mode が 'disabled' のため書き込み不可"
    if dry_run:
        return False, "dry_run=True のため書き込み不可（プレビューのみ）"
    if not manual_execute:
        return False, "manual_execute=False のため書き込み不可（手動承認が必要）"
    if not allow_write:
        return False, "allow_write=False のため書き込み不可（Phase 4-1: 読み取り専用）"
    return True, "書き込み条件を満たしています"


def write_rows(
    sheet_name: str,
    rows: list[dict],
    *,
    dry_run: bool = True,
    manual_execute: bool = False,
    allow_write: bool = False,
    settings: dict | None = None,
) -> dict:
    """Write rows to a Google Sheet.

    Default: preview-only (dry_run=True, manual_execute=False, allow_write=False).
    Phase 4-1: allow_write always defaults False — read-only phase.
    Phase 4-2+: allow_write=True enables actual writes when all other guards pass.
    """
    auth_cfg = get_auth_config(settings)
    auth_mode = auth_cfg["auth_mode"]
    can_write, reason = _can_write(auth_mode, dry_run, manual_execute, allow_write)

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
        "phase":         "Phase 4-1 (read-only; writes blocked by allow_write=False)",
        "note":          "Writes enabled in Phase 4-2+ when allow_write=True and all guards pass",
    }
