"""sheet_reader — Google Sheets read abstraction for Creator Factory OS (v5.2 Phase 4-3).

If auth_mode == 'disabled' (committed default): returns dry-run sample data. No API call.
If auth_mode == 'service_account' (local override via workspace_local.json): live gspread read.
If gspread is not installed: returns a safe error, never crashes.
If credential file is missing: returns a safe error, never crashes.
Phase 4-4+: OAuth read support.
"""
from __future__ import annotations

from src.workspace.google_auth import (
    get_auth_config, get_credential_status, get_dependency_status, build_client,
)

# Sample data returned in dry-run / disabled mode (mirrors column mappings in sheets_sync.py)
SAMPLE_SHEET_DATA: dict[str, list[dict]] = {
    "KPI": [
        {"日付": "2026-06-27", "売上目標": "100000", "動画本数目標": "3",
         "note記事目標": "2", "SNS投稿目標": "3"},
    ],
    "Revenue": [
        {"今日の売上": "0", "今日の経費": "0", "月間売上": "0", "月間経費": "0"},
    ],
    "Notes": [
        {"記事ID": "sample-001", "タイトル": "サンプル記事", "ステータス": "draft",
         "公開日": "", "収益": "0", "スコア": "0"},
    ],
    "SNS": [
        {"投稿ID": "sample-001", "プラットフォーム": "X", "ステータス": "draft",
         "公開日": ""},
    ],
    "Sales": [
        {"リードID": "sample-001", "名前": "サンプルリード", "ステータス": "new",
         "ソース": "", "作成日": ""},
    ],
}


def read_sheet(sheet_name: str, settings: dict | None = None) -> tuple[list[dict], str | None]:
    """Read rows from a Google Sheet. Returns (rows, error_or_None).

    auth_mode == 'disabled' → sample data, no API call.
    auth_mode == 'service_account' → real gspread read (Phase 4-1).
    Never crashes; returns ([], error_str) on any failure.
    """
    auth_cfg = get_auth_config(settings)

    if auth_cfg["auth_mode"] == "disabled":
        return SAMPLE_SHEET_DATA.get(sheet_name, []), None

    # Dependency guard
    deps = get_dependency_status()
    if not deps["all_ready"]:
        missing = ", ".join(deps["missing"])
        return [], f"依存パッケージが不足しています: {missing} → {deps['install_hint']}"

    cred = get_credential_status(settings)
    if not cred["ready"]:
        return [], f"認証エラー: {cred['label']}"

    # Build live client
    client_result = build_client(settings)
    if client_result["status"] != "connected":
        return [], client_result.get("error") or f"接続エラー: {client_result['status']}"

    # Resolve spreadsheet_id (use merged settings so local workspace_local.json is honoured)
    if settings is None:
        from src.workspace.sync_validator import load_merged_settings as _lm
        settings = _lm()
    spreadsheet_id = (
        settings.get("google_sheets", {}).get("spreadsheet_id", "").strip()
        or settings.get("spreadsheet_id", "").strip()
    )
    if not spreadsheet_id:
        return [], "spreadsheet_id が設定されていません。config/workspace_settings.json の google_sheets.spreadsheet_id を設定してください。"

    try:
        client = client_result["client"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        rows = worksheet.get_all_records()
        return list(rows), None
    except Exception as exc:
        return [], f"シート読み取りエラー ({sheet_name}): {type(exc).__name__}: {exc}"


def read_sheet_detail(
    sheet_name: str,
    settings: dict | None = None,
) -> dict:
    """Read a sheet and return a rich status dict. Never crashes.

    Returns:
      ok          — bool
      rows        — list[dict]
      row_count   — int
      source      — "live" | "sample" | "error"
      error       — str | None
      sheet_name  — str
      auth_mode   — str
    """
    auth_cfg = get_auth_config(settings)
    auth_mode = auth_cfg["auth_mode"]

    try:
        rows, err = read_sheet(sheet_name, settings)
        source = "sample" if auth_mode == "disabled" else ("live" if not err else "error")
        return {
            "ok":         err is None,
            "rows":       rows,
            "row_count":  len(rows),
            "source":     source,
            "error":      err,
            "sheet_name": sheet_name,
            "auth_mode":  auth_mode,
        }
    except Exception as exc:
        return {
            "ok":         False,
            "rows":       [],
            "row_count":  0,
            "source":     "error",
            "error":      f"内部エラー: {exc}",
            "sheet_name": sheet_name,
            "auth_mode":  auth_mode,
        }


def get_reader_status(settings: dict | None = None) -> dict:
    """Return reader readiness status. No side effects, never raises."""
    try:
        auth_cfg = get_auth_config(settings)
        cred     = get_credential_status(settings)
        deps     = get_dependency_status()
        dry_run  = auth_cfg["auth_mode"] == "disabled"
        return {
            "auth_mode":        auth_cfg["auth_mode"],
            "dry_run_mode":     dry_run,
            "credential_ready": cred["ready"],
            "deps_ready":       deps["all_ready"],
            "status":           "dry_run" if dry_run else cred["status"],
            "label":            "ドライラン（サンプルデータ）" if dry_run else cred["label"],
            "icon":             "🔍" if dry_run else cred["icon"],
            "phase":            "Phase 4-3 (live read-only connection verified)",
        }
    except Exception as exc:
        return {
            "auth_mode": "disabled", "dry_run_mode": True,
            "credential_ready": False, "deps_ready": False,
            "status": "error", "label": str(exc), "icon": "🔴",
            "phase": "Phase 4-3",
        }
