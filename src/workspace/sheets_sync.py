"""sheets_sync — Google Sheets マッピング定義とローカルデータ読み込み (v5.2 Phase 4-5)

ローカルJSONフィールドがGoogle Sheetsの列にどのようにマッピングされるかを定義する。
APIコールはここでは行わない。実際のSheets書き込みはPhase 4-4以降（google-auth + gspread）が必要。

Phase 4-5 追加:
  - SHEET_MAPPINGS: 実データに合わせてマッピング列名・key_fieldを修正
  - extract_flat_row(): ネスト構造をフラット行に変換（ターゲット別ロジック）
  - read_flat_rows(): Phase 4-5専用ローダー（extract_flat_row込み）
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

# target_id → シートマッピング設定
# Phase 4-5: 実際のJSONデータ構造に合わせて列定義を修正済み
SHEET_MAPPINGS: dict[str, dict] = {
    "kpi_targets": {
        "sheet_name": "KPI",
        "data_key":   None,      # ルートdictが対象（targets/actualsネストあり）
        "key_field":  "date",
        "columns": [
            ("date",         "日付"),
            ("sales_target", "売上目標"),
            ("note_posts",   "note記事目標"),
            ("video_count",  "動画本数目標"),
            ("sns_posts",    "SNS投稿目標"),
            ("sales_calls",  "営業コール目標"),
            ("dev_tasks",    "開発タスク目標"),
        ],
    },
    "revenue_expense": {
        "sheet_name": "Revenue",
        "data_key":   None,      # today サブdictを1行として同期
        "key_field":  "date",
        "columns": [
            ("date",    "日付"),
            ("revenue", "売上"),
            ("expense", "経費"),
        ],
    },
    "note_articles": {
        "sheet_name": "Notes",
        "data_key":   "articles",
        "key_field":  "id",      # ローカルフィールド名は "id"（"article_id" ではない）
        "columns": [
            ("id",             "記事ID"),
            ("title",          "タイトル"),
            ("status",         "ステータス"),
            ("published_at",   "公開日"),
            ("actual_revenue", "実収益"),
            ("score_total",    "スコア合計"),
            ("score_grade",    "スコアグレード"),
            ("view_count",     "閲覧数"),
            ("like_count",     "いいね数"),
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


def extract_flat_row(target_id: str, raw_row: dict) -> dict:
    """ネスト構造を含むローカルJSON行をシート用フラット行に変換する。

    kpi_targets:     {date, targets:{...}, actuals:{...}} → フラット7列
    revenue_expense: {today:{date, revenue, expense}, ...} → today を3列で返す
    note_articles:   score ネストをフラット化、フィールド名を列定義に統一
    その他:          そのまま返す（変換なし）
    """
    if target_id == "kpi_targets":
        targets = raw_row.get("targets") or {}
        return {
            "date":         str(raw_row.get("date", "")),
            "sales_target": targets.get("sales_target", 0),
            "note_posts":   targets.get("note_posts", 0),
            "video_count":  targets.get("video_count", 0),
            "sns_posts":    targets.get("sns_posts", 0),
            "sales_calls":  targets.get("sales_calls", 0),
            "dev_tasks":    targets.get("dev_tasks", 0),
        }

    if target_id == "revenue_expense":
        # today サブdictを1行として扱う
        today = raw_row.get("today") or raw_row
        return {
            "date":    str(today.get("date", raw_row.get("date", ""))),
            "revenue": today.get("revenue", 0),
            "expense": today.get("expense", 0),
        }

    if target_id == "note_articles":
        # score は nested dict → score_total / score_grade にフラット化
        score = raw_row.get("score") or {}
        if isinstance(score, dict):
            score_total = score.get("total", 0)
            score_grade = str(score.get("grade", ""))
        else:
            score_total = int(score) if score else 0
            score_grade = ""
        # title の長さを上限500文字に制限（Sheetsセル上限対策）
        title = str(raw_row.get("title", ""))
        if len(title) > 500:
            title = title[:500]
        return {
            "id":             str(raw_row.get("id", raw_row.get("article_id", ""))),
            "title":          title,
            "status":         str(raw_row.get("status", "")),
            "published_at":   str(raw_row.get("published_at") or ""),
            "actual_revenue": raw_row.get("actual_revenue", 0),
            "score_total":    score_total,
            "score_grade":    score_grade,
            "view_count":     raw_row.get("view_count", 0),
            "like_count":     raw_row.get("like_count", 0),
        }

    return raw_row


def read_flat_rows(target_id: str, local_file: str) -> tuple[list[dict], str | None]:
    """Phase 4-5専用: ローカルJSONを読み込み、extract_flat_row済みのフラット行リストを返す。

    read_local_data() とは異なり、各ターゲットのネスト構造を正しく処理する。
    APIコールなし。書き込みなし。純粋なファイル読み取り。
    """
    path = ROOT / local_file
    if not path.exists():
        return [], f"ファイルが見つかりません: {local_file}"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [], f"JSONパースエラー: {exc}"

    mapping = SHEET_MAPPINGS.get(target_id)
    if not mapping:
        return [], f"マッピングが未定義: {target_id}"

    # revenue_expense は today の1行のみを同期対象とする
    if target_id == "revenue_expense":
        today = (raw.get("today") or {}) if isinstance(raw, dict) else {}
        if not today:
            return [], "revenue_expense.json の today データが空です"
        return [extract_flat_row(target_id, raw)], None

    # その他: data_key に従ってリストを抽出してフラット化
    data_key = mapping.get("data_key")
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict) and data_key and isinstance(raw.get(data_key), list):
        items = raw[data_key]
    elif isinstance(raw, dict):
        items = [raw]
    else:
        return [], f"未対応のデータ形式: {type(raw).__name__}"

    flat_rows = [extract_flat_row(target_id, r) for r in items]
    return flat_rows, None


def read_local_data(local_file: str) -> tuple[list[dict], str | None]:
    """ローカルJSONファイルを読み込み (rows, error) を返す。APIコールなし。

    run_preview() で使用する従来関数。Phase 4-5 では read_flat_rows() を使用すること。
    history キーが空リストの場合は無視し、ルートdictを返す（revenue_expense 対応）。
    """
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
        # 空でないリストを持つキーを探す（historyキーが空の場合は飛ばす）
        for key in ("articles", "posts", "leads", "deals", "workflows", "tasks"):
            if isinstance(raw.get(key), list) and raw.get(key):
                return raw[key], None
        return [raw], None
    return [], "未対応のデータ形式"


def prepare_mapping(target_id: str, local_file: str) -> dict:
    """カラムマッピングプレビューをローカルデータから生成する。読み取り専用。APIコールなし。"""
    rows, error = read_local_data(local_file)
    mapping = get_mapping(target_id)

    if error:
        return {"target_id": target_id, "ready": False, "error": error,
                "rows": [], "row_count": 0, "columns": [], "sheet_name": ""}

    sheet_name = mapping["sheet_name"] if mapping else ""
    columns = [col for _, col in mapping["columns"]] if mapping else []
    fields  = [field for field, _ in mapping["columns"]] if mapping else []

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
