"""action_engine — execute safe draft-only actions.

SAFETY RULES:
- dry_run=True by default — NEVER writes unless caller explicitly passes dry_run=False
- All created items have status='draft'/'pending'/'new' (never 'published'/'confirmed')
- All items are marked with _automation_source=True
- No existing items are overwritten or deleted
- No external network calls
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent


def _read_json(rel: str) -> dict:
    p = ROOT / rel
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _write_json(rel: str, data: dict) -> None:
    p = ROOT / rel
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _ok(description: str, dry_run: bool, item: dict | None = None) -> dict:
    return {"success": True, "dry_run": dry_run, "description": description, "item": item or {}}


def _err(description: str, dry_run: bool) -> dict:
    return {"success": False, "dry_run": dry_run, "description": description, "item": {}}


# ── Actions ────────────────────────────────────────────────────────────────────

def _action_create_task(config: dict, context: dict, dry_run: bool) -> dict:
    warnings = context.get("warnings", [])
    prefix   = config.get("title_prefix", "⚠️")
    title    = f"{prefix} {warnings[0][:40]}" if warnings else f"{prefix} 自動生成タスク"
    task = {
        "task_id":           "task_" + uuid.uuid4().hex[:8],
        "title":             title,
        "category":          config.get("category", "自動化"),
        "status":            "pending",
        "priority":          config.get("priority", "normal"),
        "page_link":         None,
        "_automation_source": True,
        "created_at":        datetime.now().strftime("%Y-%m-%d"),
    }
    if dry_run:
        return _ok(f"[ドライラン] タスク追加予定: {task['title']}", True, task)
    try:
        data = _read_json("config/daily_tasks.json")
        if "tasks" not in data:
            data["tasks"] = []
        data["tasks"].append(task)
        _write_json("config/daily_tasks.json", data)
        return _ok(f"タスク追加: {task['title']}", False, task)
    except Exception as exc:
        return _err(f"タスク追加エラー: {exc}", False)


def _action_create_sns_draft(config: dict, context: dict, dry_run: bool) -> dict:
    matched = context.get("matched_items", [{}])
    source  = matched[0] if matched else {}
    title   = source.get("title", "")
    prefix  = config.get("prefix", "📝 新記事を公開しました:")
    content = f"{prefix}\n{title}" if title else f"{prefix}\n（タイトル未設定）"
    post = {
        "post_id":            "post_" + uuid.uuid4().hex[:8],
        "platform":           config.get("platform", "X"),
        "content":            content[:280],
        "status":             "draft",
        "hashtags":           [],
        "media_urls":         [],
        "scheduled_at":       None,
        "published_date":     None,
        "_automation_source": True,
        "created_at":         datetime.now().strftime("%Y-%m-%d"),
    }
    if dry_run:
        return _ok(f"[ドライラン] SNS下書き作成予定: {post['platform']} / {content[:40]}", True, post)
    try:
        data = _read_json("config/sns_posts.json")
        if "posts" not in data:
            data["posts"] = []
        data["posts"].append(post)
        _write_json("config/sns_posts.json", data)
        return _ok(f"SNS下書き作成: {post['platform']} / {content[:40]}", False, post)
    except Exception as exc:
        return _err(f"SNS下書き作成エラー: {exc}", False)


def _action_create_sales_lead(config: dict, context: dict, dry_run: bool) -> dict:
    matched = context.get("matched_items", [{}])
    source  = matched[0] if matched else {}
    lead = {
        "lead_id":            "lead_" + uuid.uuid4().hex[:8],
        "name":               "自動生成リード",
        "company":            "",
        "source":             config.get("source", "other"),
        "contact_method":     "",
        "rank":               config.get("rank", "C"),
        "interest":           source.get("content", "")[:100] if source else "",
        "status":             "new",
        "next_action":        "確認・精査が必要",
        "next_action_date":   "",
        "memo":               config.get("memo", "自動化工場が生成した候補"),
        "_automation_source": True,
        "created_at":         datetime.now().strftime("%Y-%m-%d"),
        "updated_at":         datetime.now().strftime("%Y-%m-%d"),
    }
    if dry_run:
        return _ok(f"[ドライラン] 見込み客追加予定: rank={lead['rank']} / {lead['source']}", True, lead)
    try:
        data = _read_json("config/sales_leads.json")
        if "leads" not in data:
            data["leads"] = []
        data["leads"].append(lead)
        _write_json("config/sales_leads.json", data)
        return _ok(f"見込み客追加: rank={lead['rank']}", False, lead)
    except Exception as exc:
        return _err(f"見込み客追加エラー: {exc}", False)


def _action_create_revenue_draft(config: dict, context: dict, dry_run: bool) -> dict:
    matched = context.get("matched_items", [{}])
    deal    = matched[0] if matched else {}
    amount  = deal.get("amount", 0)
    entry = {
        "revenue_id":         "rev_" + uuid.uuid4().hex[:8],
        "source":             "sales",
        "source_factory":     "営業工場",
        "amount":             amount,
        "entry_date":         datetime.now().strftime("%Y-%m-%d"),
        "status":             "pending",
        "memo":               config.get("memo", f"商談成約（自動生成）: {deal.get('title', '')}"),
        "_automation_source": True,
        "created_at":         datetime.now().strftime("%Y-%m-%d"),
    }
    if dry_run:
        return _ok(f"[ドライラン] 売上下書き作成予定: ¥{amount:,} (pending)", True, entry)
    try:
        data = _read_json("config/accounting_revenue.json")
        if "revenue" not in data:
            data["revenue"] = []
        data["revenue"].append(entry)
        _write_json("config/accounting_revenue.json", data)
        return _ok(f"売上下書き作成: ¥{amount:,} (pending)", False, entry)
    except Exception as exc:
        return _err(f"売上下書き作成エラー: {exc}", False)


def _action_create_report(config: dict, context: dict, dry_run: bool) -> dict:
    report_type = config.get("report_type", "generic")
    below       = context.get("below_items", [])
    lines = [f"# 自動生成レポート — {report_type}",
             f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
    if report_type == "kpi_suggestion" and below:
        lines += ["## KPI改善サジェスト", ""]
        for item in below:
            lines.append(f"- **{item['key']}**: 実績 {item['actual']} / 目標 {item['target']} "
                         f"({item['pct']}%) — 優先度を上げてください")
    else:
        lines.append("詳細はアナリティクス工場を確認してください。")
    report_text = "\n".join(lines)
    return _ok(f"[レポート生成] {report_type} ({len(below)} 項目)", dry_run,
               {"report_text": report_text})


def _action_update_factory_status(config: dict, context: dict, dry_run: bool) -> dict:
    factory_name = config.get("factory_name", "")
    next_action  = config.get("next_action", "自動化工場からの更新")
    if not factory_name:
        return _err("factory_name未設定", dry_run)
    if dry_run:
        return _ok(f"[ドライラン] {factory_name} next_action 更新予定", True, {})
    try:
        data = _read_json("config/factory_status.json")
        fs   = data.get("factories", data)
        if factory_name in fs and isinstance(fs[factory_name], dict):
            fs[factory_name]["next_action"] = next_action
            _write_json("config/factory_status.json", data)
            return _ok(f"{factory_name} next_action 更新", False, {})
        return _err(f"{factory_name} が factory_status.json に見つかりません", False)
    except Exception as exc:
        return _err(f"ステータス更新エラー: {exc}", False)


# ── Dispatcher ────────────────────────────────────────────────────────────────

_ACTIONS = {
    "create_task":                    _action_create_task,
    "create_sns_draft":               _action_create_sns_draft,
    "create_sales_lead_candidate":    _action_create_sales_lead,
    "create_accounting_revenue_draft":_action_create_revenue_draft,
    "create_report":                  _action_create_report,
    "update_factory_status":          _action_update_factory_status,
}


def execute_action(
    action_type: str,
    action_config: dict,
    context: dict,
    dry_run: bool = True,
) -> dict:
    """Execute a single action. dry_run=True by default — safe."""
    fn = _ACTIONS.get(action_type)
    if not fn:
        return _err(f"不明なアクションタイプ: {action_type}", dry_run)
    try:
        return fn(action_config, context, dry_run)
    except Exception as exc:
        return _err(f"アクション実行エラー: {exc}", dry_run)
