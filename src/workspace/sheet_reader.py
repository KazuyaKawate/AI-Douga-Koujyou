"""sheet_reader — Google Sheets read abstraction for Creator Factory OS (v5.2 Phase 2).

If auth_mode == 'disabled' (default): returns dry-run sample data. No API call.
Phase 3+: will call the Google Sheets API when credentials are configured.
"""
from __future__ import annotations

from src.workspace.google_auth import get_auth_config, get_credential_status

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
    """Read rows from a Google Sheet.

    Returns (rows, error).
    auth_mode == 'disabled' → sample data, no API call.
    Phase 3+: calls Google Sheets API when credentials are ready.
    """
    auth_cfg = get_auth_config(settings)

    if auth_cfg["auth_mode"] == "disabled":
        return SAMPLE_SHEET_DATA.get(sheet_name, []), None

    cred = get_credential_status(settings)
    if not cred["ready"]:
        return [], f"認証エラー: {cred['label']}"

    # Phase 3+: actual API call here (gspread / google-api-python-client).
    return SAMPLE_SHEET_DATA.get(sheet_name, []), None


def get_reader_status(settings: dict | None = None) -> dict:
    """Return reader readiness status. No side effects."""
    auth_cfg = get_auth_config(settings)
    cred = get_credential_status(settings)
    dry_run = auth_cfg["auth_mode"] == "disabled"
    return {
        "auth_mode":        auth_cfg["auth_mode"],
        "dry_run_mode":     dry_run,
        "credential_ready": cred["ready"],
        "status":           "dry_run" if dry_run else cred["status"],
        "label":            "ドライラン（サンプルデータ）" if dry_run else cred["label"],
        "icon":             "🔍" if dry_run else cred["icon"],
    }
