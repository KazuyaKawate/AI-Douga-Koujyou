"""Factory Status — loads and saves factory status cards from config/factory_status.json."""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "factory_status.json"

FACTORIES = ["AI動画工場", "note投稿工場", "SNS投稿工場", "営業工場", "会計監査工場", "CEO Dashboard"]

FACTORY_ICONS = {
    "AI動画工場":    "🎬",
    "note投稿工場":  "📝",
    "SNS投稿工場":   "📱",
    "営業工場":      "💼",
    "会計監査工場":  "💰",
    "CEO Dashboard": "🎯",
}

STATUS_COLORS = {
    "active":  "🟢",
    "idle":    "🟡",
    "warning": "🔴",
    "stopped": "⚫",
}

_DEFAULTS = {
    "AI動画工場":    {"status": "idle", "active_items": 0, "completed_today": 0, "warning_count": 0, "next_action": "動画を制作してください"},
    "note投稿工場":  {"status": "idle", "active_items": 0, "completed_today": 0, "warning_count": 0, "next_action": "記事を作成してください"},
    "SNS投稿工場":   {"status": "idle", "active_items": 0, "completed_today": 0, "warning_count": 0, "next_action": "投稿を作成してください"},
    "営業工場":      {"status": "idle", "active_items": 0, "completed_today": 0, "warning_count": 0, "next_action": "営業活動を開始してください"},
    "会計監査工場":  {"status": "idle", "active_items": 0, "completed_today": 0, "warning_count": 0, "next_action": "収支を確認してください"},
    "CEO Dashboard": {"status": "active", "active_items": 1, "completed_today": 0, "warning_count": 0, "next_action": "KPIを確認してください"},
}


def load_factory_status() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            for factory, defaults in _DEFAULTS.items():
                if factory not in data:
                    data[factory] = defaults.copy()
            return data
        except Exception:
            pass
    data = {k: v.copy() for k, v in _DEFAULTS.items()}
    _save(data)
    return data


def save_factory_status(data: dict) -> None:
    _save(data)


def _save(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sync_from_tasks(factory_data: dict, tasks_data: dict) -> dict:
    """Sync factory completed/active counts from task data."""
    from src.hq.task_manager import CATEGORIES
    cat_map = {
        "AI動画工場":   "AI動画工場",
        "note投稿工場": "note投稿工場",
        "SNS投稿工場":  "SNS投稿工場",
        "営業工場":     "営業工場",
        "会計監査工場": "会計監査工場",
    }
    tasks = tasks_data.get("tasks", [])
    for cat, factory_key in cat_map.items():
        cat_tasks = [t for t in tasks if t.get("category") == cat]
        done = sum(1 for t in cat_tasks if t["status"] == "done")
        active = sum(1 for t in cat_tasks if t["status"] == "in_progress")
        if factory_key in factory_data:
            factory_data[factory_key]["completed_today"] = done
            factory_data[factory_key]["active_items"] = active
            if done > 0 or active > 0:
                factory_data[factory_key]["status"] = "active"
    return factory_data


def sync_from_sns(factory_data: dict) -> dict:
    """Sync SNS投稿工場 factory status from SNS post data (optional import)."""
    try:
        from src.factories.sns.sns_post_manager import load_posts, get_factory_summary
        sns_data = load_posts()
        summary = get_factory_summary(sns_data)
        if "SNS投稿工場" in factory_data:
            fd = factory_data["SNS投稿工場"]
            fd["completed_today"] = summary.get("published_today", 0)
            fd["active_items"] = summary.get("scheduled", 0)
            fd["warning_count"] = summary.get("warnings", 0)
            if fd["completed_today"] > 0:
                fd["status"] = "active"
                fd["next_action"] = f"本日{fd['completed_today']}件公開済"
            elif fd["active_items"] > 0:
                fd["status"] = "active"
                fd["next_action"] = f"{fd['active_items']}件のスケジュール投稿あり"
            if fd["warning_count"] > 0:
                fd["status"] = "warning"
                fd["next_action"] = f"⚠️ {fd['warning_count']}件の投稿が期限超過"
    except Exception:
        pass
    return factory_data


def sync_from_notes(factory_data: dict) -> dict:
    """Sync note投稿工場 factory status from article data (optional import)."""
    try:
        from src.factories.note.article_manager import load_articles, get_factory_summary
        note_data = load_articles()
        summary = get_factory_summary(note_data)
        if "note投稿工場" in factory_data:
            fd = factory_data["note投稿工場"]
            fd["completed_today"] = summary.get("published_today", 0)
            fd["active_items"] = summary.get("reviewing", 0) + summary.get("scheduled", 0)
            if fd["completed_today"] > 0:
                fd["status"] = "active"
                fd["next_action"] = f"本日{fd['completed_today']}件公開済"
            elif fd["active_items"] > 0:
                fd["status"] = "active"
                fd["next_action"] = f"{fd['active_items']}件のレビュー/スケジュール中"
    except Exception:
        pass
    return factory_data


def sync_from_sales(factory_data: dict) -> dict:
    """Sync 営業工場 factory status from sales data (optional import)."""
    try:
        from src.factories.sales.lead_manager import load_leads, get_factory_summary as lead_sum
        from src.factories.sales.followup_manager import load_followups, get_followup_summary
        leads_data = load_leads()
        followups_data = load_followups()
        l_summary = lead_sum(leads_data)
        fu_summary = get_followup_summary(followups_data)
        if "営業工場" in factory_data:
            fd = factory_data["営業工場"]
            fd["active_items"] = l_summary.get("active", 0)
            fd["warning_count"] = fu_summary.get("overdue", 0)
            needs = fu_summary.get("needs_followup", 0)
            if fd["warning_count"] > 0:
                fd["status"] = "warning"
                fd["next_action"] = f"⚠️ {fd['warning_count']}件のフォロー期限超過"
            elif needs > 0:
                fd["status"] = "active"
                fd["next_action"] = f"今日のフォロー: {needs}件"
            elif fd["active_items"] > 0:
                fd["status"] = "active"
                fd["next_action"] = f"進行中商談: {fd['active_items']}件"
    except Exception:
        pass
    return factory_data


def sync_from_accounting(factory_data: dict) -> dict:
    """Sync 会計監査工場 factory status from accounting data (optional import)."""
    try:
        from src.factories.accounting.revenue_manager import load_revenue, get_factory_summary as rev_sum
        from src.factories.accounting.audit_checker import check_audits, get_audit_summary
        from src.factories.accounting.expense_manager import load_expenses
        from src.factories.accounting.subscription_manager import load_subscriptions
        rev_data = load_revenue()
        exp_data = load_expenses()
        sub_data = load_subscriptions()
        r_s = rev_sum(rev_data)
        warnings = check_audits(rev_data, exp_data, sub_data)
        audit_s = get_audit_summary(warnings)
        if "会計監査工場" in factory_data:
            fd = factory_data["会計監査工場"]
            fd["completed_today"] = 1 if r_s["today_revenue"] > 0 else 0
            fd["active_items"] = r_s["confirmed_count"]
            fd["warning_count"] = audit_s["errors"] + audit_s["warning"]
            if fd["warning_count"] > 0:
                fd["status"] = "warning"
                fd["next_action"] = f"⚠️ 監査アラート {fd['warning_count']}件"
            elif r_s["today_revenue"] > 0:
                fd["status"] = "active"
                fd["next_action"] = f"本日売上 ¥{r_s['today_revenue']:,}"
            elif r_s["month_revenue"] > 0:
                fd["status"] = "active"
                fd["next_action"] = f"今月売上 ¥{r_s['month_revenue']:,}"
    except Exception:
        pass
    return factory_data
