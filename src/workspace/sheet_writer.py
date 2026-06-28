"""sheet_writer — Google Sheets write abstraction for Creator Factory OS (v5.2 Phase 4-3).

QUAD-LOCK WRITE GUARD (all four must be true to write):
  1. auth_mode != 'disabled'
  2. dry_run == False
  3. manual_execute == True
  4. allow_write == True   ← Phase 4-3: always False by default; Phase 4-4+ may enable writes

DEPENDENCY GUARDS (checked after quad-lock):
  5. gspread installed
  6. google-auth installed
  7. credential file exists

Default behavior is always preview-only. Never crashes UI. Never writes by accident.
Actual writes remain Phase 4-4+ (Phase 4-3 = live read-only connection verified).
"""
from __future__ import annotations

from src.workspace.google_auth import get_auth_config, get_credential_status, get_dependency_status, build_client


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
        return False, "allow_write=False のため書き込み不可（Phase 4-3: 読み取り専用）"
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
    Phase 4-3: allow_write always defaults False — read-only phase.
    Phase 4-4+: allow_write=True enables actual writes when all other guards pass.
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

    # Resolve settings for spreadsheet_id lookup
    _write_settings = settings
    if _write_settings is None:
        from src.workspace.sync_validator import load_merged_settings as _lms_w
        _write_settings = _lms_w()

    # Actual gspread append (Phase 4-4+)
    try:
        client_result = build_client(_write_settings)
        if client_result["status"] != "connected":
            base["reason"] = f"接続エラー: {client_result['status']}"
            return base
        spreadsheet_id = (
            _write_settings.get("google_sheets", {}).get("spreadsheet_id", "").strip()
            or _write_settings.get("spreadsheet_id", "").strip()
        )
        if not spreadsheet_id:
            base["reason"] = "spreadsheet_id が未設定です。config/workspace_local.json を確認してください。"
            return base
        client       = client_result["client"]
        spreadsheet  = client.open_by_key(spreadsheet_id)
        worksheet_obj = spreadsheet.worksheet(sheet_name)
        for row in rows:
            values = list(row.values())
            worksheet_obj.append_row(values, value_input_option="USER_ENTERED")
        base["executed"]     = True
        base["rows_written"] = len(rows)
        base["reason"]       = f"{len(rows)}行を追記しました（シート: {sheet_name}）"
    except Exception as exc:
        base["reason"] = f"書き込みエラー: {type(exc).__name__}: {exc}"
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
        "allow_write":   False,
        "phase":         "Phase 4-4 (test worksheet append; allow_write=False in committed code)",
        "note":          "allow_write=True is passed only from the UI write button — never committed",
    }
