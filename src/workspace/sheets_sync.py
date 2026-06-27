"""sheets_sync — Google Sheets mapping definitions and local data reader (v5.2).

Defines how local JSON fields map to Google Sheets columns.
No API calls are made here. Actual Sheets writes require Phase 2 (google-auth + gspread).
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

# Maps target_id → sheet mapping config
SHEET_MAPPINGS: dict[str, dict] = {
    "kpi_targets": {
        "sheet_name": "KPI",
        "data_key":   None,
        "key_field":  "date",
        "columns": [
            ("date",                 "日付"),
            ("revenue_target",       "売上目標"),
            ("video_count_target",   "動画本数目標"),
            ("note_count_target",    "note記事目標"),
            ("sns_post_target",      "SNS投稿目標"),
        ],
    },
    "revenue_expense": {
        "sheet_name": "Revenue",
        "data_key":   None,
        "key_field":  "id",
        "columns": [
            ("today.revenue",  "今日の売上"),
            ("today.expense",  "今日の経費"),
            ("month.revenue",  "月間売上"),
            ("month.expense",  "月間経費"),
        ],
    },
    "note_articles": {
        "sheet_name": "Notes",
        "data_key":   "articles",
        "key_field":  "article_id",
        "columns": [
            ("article_id",     "記事ID"),
            ("title",          "タイトル"),
            ("status",         "ステータス"),
            ("published_date", "公開日"),
            ("revenue",        "収益"),
            ("score",          "スコア"),
        ],
    },
    "sns_posts": {
        "sheet_name": "SNS",
        "data_key":   "posts",
        "key_field":  "post_id",
        "columns": [
            ("post_id",        "投稿ID"),
            ("platform",       "プラットフォーム"),
            ("status",         "ステータス"),
            ("published_date", "公開日"),
        ],
    },
    "sales_leads": {
        "sheet_name": "Sales",
        "data_key":   "leads",
        "key_field":  "lead_id",
        "columns": [
            ("lead_id",      "リードID"),
            ("name",         "名前"),
            ("status",       "ステータス"),
            ("source",       "ソース"),
            ("created_date", "作成日"),
        ],
    },
}


def get_mapping(target_id: str) -> dict | None:
    return SHEET_MAPPINGS.get(target_id)


def read_local_data(local_file: str) -> tuple[list[dict], str | None]:
    """Read a local JSON file and return (rows, error). Never calls any API."""
    path = ROOT / local_file
    if not path.exists():
        return [], f"ファイルが見つかりません: {local_file}"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [], f"JSONパースエラー: {exc}"

    if isinstance(raw, list):
        return raw, None
    if isinstance(raw, dict):
        for key in ("articles", "posts", "leads", "deals", "workflows", "history", "tasks"):
            if isinstance(raw.get(key), list):
                return raw[key], None
        return [raw], None
    return [], "未対応のデータ形式"


def prepare_mapping(target_id: str, local_file: str) -> dict:
    """Build a column-mapping preview from local data. Read-only. No API calls."""
    rows, error = read_local_data(local_file)
    mapping = get_mapping(target_id)

    if error:
        return {"target_id": target_id, "ready": False, "error": error,
                "rows": [], "row_count": 0, "columns": [], "sheet_name": ""}

    sheet_name = mapping["sheet_name"] if mapping else ""
    columns = [col for _, col in mapping["columns"]] if mapping else []
    fields = [field for field, _ in mapping["columns"]] if mapping else []

    return {
        "target_id":  target_id,
        "sheet_name": sheet_name,
        "columns":    columns,
        "fields":     fields,
        "rows":       rows,
        "row_count":  len(rows),
        "ready":      True,
        "error":      None,
    }
