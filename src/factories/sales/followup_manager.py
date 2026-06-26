"""Follow-up manager — overdue detection, today/week views, mark-done with KPI side-effect."""
import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "sales_followups.json"

FOLLOWUP_TYPES = ["email", "DM", "phone", "Zoom", "meeting", "LINE", "other"]
TYPE_LABELS = {
    "email":   "📧 メール",
    "DM":      "💬 DM",
    "phone":   "📞 電話",
    "Zoom":    "🖥️ Zoom",
    "meeting": "🤝 対面",
    "LINE":    "💚 LINE",
    "other":   "🔹 その他",
}

FOLLOWUP_STATUSES = ["pending", "done", "skipped"]
STATUS_LABELS = {"pending": "⏳ 未完了", "done": "✅ 完了", "skipped": "⏭️ スキップ"}


def load_followups() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"followups": [], "meta": {"version": "4.5"}}


def save_followups(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_followup(
    lead_id: str,
    description: str,
    due_date: str,
    followup_type: str = "email",
    deal_id: str = "",
) -> dict:
    data = load_followups()
    now = datetime.now().isoformat(timespec="seconds")
    fu = {
        "followup_id": "fu_" + uuid.uuid4().hex[:8],
        "lead_id":     lead_id,
        "deal_id":     deal_id,
        "type":        followup_type,
        "description": description,
        "due_date":    due_date,
        "status":      "pending",
        "done_at":     None,
        "created_at":  now,
        "updated_at":  now,
    }
    data["followups"].append(fu)
    save_followups(data)
    return fu


def mark_done_followup(followup_id: str) -> tuple[bool, str]:
    data = load_followups()
    now = datetime.now().isoformat(timespec="seconds")
    for fu in data["followups"]:
        if fu["followup_id"] == followup_id:
            if fu["status"] == "done":
                return False, "すでに完了済みです"
            fu["status"] = "done"
            fu["done_at"] = now
            fu["updated_at"] = now
            save_followups(data)
            _on_followup_done(fu)
            _update_lead_timestamp(fu.get("lead_id", ""))
            return True, "フォローアップを完了しました"
    return False, f"フォローアップ {followup_id} が見つかりません"


def skip_followup(followup_id: str) -> bool:
    data = load_followups()
    for fu in data["followups"]:
        if fu["followup_id"] == followup_id:
            fu["status"] = "skipped"
            fu["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_followups(data)
            return True
    return False


def get_overdue_followups(data: dict) -> list[dict]:
    today = date.today().isoformat()
    return [
        fu for fu in data.get("followups", [])
        if fu.get("status") == "pending"
        and fu.get("due_date", "9999-12-31") < today
    ]


def get_today_followups(data: dict) -> list[dict]:
    today = date.today().isoformat()
    return [
        fu for fu in data.get("followups", [])
        if fu.get("status") == "pending"
        and fu.get("due_date") == today
    ]


def get_week_followups(data: dict) -> list[dict]:
    today = date.today()
    week_end = (today + timedelta(days=7)).isoformat()
    today_str = today.isoformat()
    return [
        fu for fu in data.get("followups", [])
        if fu.get("status") == "pending"
        and today_str <= fu.get("due_date", "") <= week_end
    ]


def get_followup_summary(data: dict) -> dict:
    followups = data.get("followups", [])
    overdue = get_overdue_followups(data)
    today_list = get_today_followups(data)
    return {
        "total":   len(followups),
        "pending": sum(1 for f in followups if f.get("status") == "pending"),
        "done":    sum(1 for f in followups if f.get("status") == "done"),
        "overdue": len(overdue),
        "today":   len(today_list),
        "needs_followup": len(overdue) + len(today_list),
    }


def _on_followup_done(_fu: dict) -> None:
    try:
        from src.hq.kpi_manager import load_kpi, update_actual
        kd = load_kpi()
        current = kd.get("actuals", {}).get("sales_calls", 0)
        update_actual("sales_calls", current + 1)
    except Exception:
        pass


def _update_lead_timestamp(lead_id: str) -> None:
    if not lead_id:
        return
    try:
        from src.factories.sales.lead_manager import update_lead
        update_lead(lead_id, updated_at=datetime.now().isoformat(timespec="seconds"))
    except Exception:
        pass
