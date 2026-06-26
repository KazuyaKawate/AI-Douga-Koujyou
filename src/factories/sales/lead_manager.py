"""Lead manager — CRUD for sales leads with status lifecycle."""
import json
import uuid
from datetime import date, datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "sales_leads.json"

LEAD_STATUSES = ["new", "contacted", "meeting", "proposal_sent", "negotiation", "contracted", "lost", "archived"]

STATUS_LABELS = {
    "new":           "新規",
    "contacted":     "連絡済",
    "meeting":       "商談中",
    "proposal_sent": "提案済",
    "negotiation":   "交渉中",
    "contracted":    "成約",
    "lost":          "失注",
    "archived":      "アーカイブ",
}

STATUS_ICONS = {
    "new":           "🆕",
    "contacted":     "📨",
    "meeting":       "🤝",
    "proposal_sent": "📋",
    "negotiation":   "💬",
    "contracted":    "✅",
    "lost":          "❌",
    "archived":      "📦",
}

LEAD_RANKS = ["S", "A", "B", "C"]
RANK_ICONS = {"S": "⭐", "A": "🔥", "B": "🔵", "C": "⬜"}
RANK_COLORS = {"S": "🟡", "A": "🔴", "B": "🔵", "C": "⬜"}

LEAD_SOURCES = ["note", "X", "Threads", "YouTube", "referral", "direct", "offline", "other"]
SOURCE_LABELS = {
    "note":     "📝 note",
    "X":        "𝕏 X",
    "Threads":  "🧵 Threads",
    "YouTube":  "▶️ YouTube",
    "referral": "👥 紹介",
    "direct":   "📞 直接",
    "offline":  "🏢 オフライン",
    "other":    "🔹 その他",
}


def load_leads() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"leads": [], "meta": {"version": "4.5"}}


def save_leads(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_lead(
    name: str,
    company: str = "",
    source: str = "direct",
    contact_method: str = "DM",
    rank: str = "B",
    interest: str = "",
    next_action: str = "",
    next_action_date: str = "",
    memo: str = "",
) -> dict:
    data = load_leads()
    now = datetime.now().isoformat(timespec="seconds")
    lead_id = "lead_" + uuid.uuid4().hex[:8]
    lead = {
        "lead_id":          lead_id,
        "name":             name,
        "company":          company,
        "source":           source,
        "contact_method":   contact_method,
        "status":           "new",
        "rank":             rank,
        "interest":         interest,
        "next_action":      next_action,
        "next_action_date": next_action_date,
        "memo":             memo,
        "created_at":       now,
        "updated_at":       now,
    }
    data["leads"].append(lead)
    save_leads(data)
    return lead


def update_lead(lead_id: str, **kwargs) -> dict | None:
    data = load_leads()
    for lead in data["leads"]:
        if lead["lead_id"] == lead_id:
            for k, v in kwargs.items():
                lead[k] = v
            lead["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_leads(data)
            return lead
    return None


def delete_lead(lead_id: str) -> bool:
    data = load_leads()
    before = len(data["leads"])
    data["leads"] = [l for l in data["leads"] if l["lead_id"] != lead_id]
    if len(data["leads"]) < before:
        save_leads(data)
        return True
    return False


def get_factory_summary(data: dict) -> dict:
    leads = data.get("leads", [])
    today_str = date.today().isoformat()
    return {
        "total":       len(leads),
        "new":         sum(1 for l in leads if l.get("status") == "new"),
        "active":      sum(1 for l in leads if l.get("status") in ("contacted", "meeting", "proposal_sent", "negotiation")),
        "contracted":  sum(1 for l in leads if l.get("status") == "contracted"),
        "lost":        sum(1 for l in leads if l.get("status") == "lost"),
        "needs_followup": sum(
            1 for l in leads
            if l.get("next_action_date") and l["next_action_date"] <= today_str
            and l.get("status") not in ("contracted", "lost", "archived")
        ),
    }
