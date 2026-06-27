"""Subscription manager — track recurring service costs (Claude, ChatGPT, Runway, etc.)."""
import json
import uuid
from datetime import date, datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "accounting_subscriptions.json"

PRESET_SERVICES = [
    {"name": "Claude Pro",         "monthly_cost": 3000,  "category": "AI subscription"},
    {"name": "ChatGPT Plus",       "monthly_cost": 3000,  "category": "AI subscription"},
    {"name": "Runway Gen-3",       "monthly_cost": 4000,  "category": "AI subscription"},
    {"name": "Midjourney",         "monthly_cost": 1500,  "category": "AI subscription"},
    {"name": "note Pro",           "monthly_cost": 500,   "category": "software"},
    {"name": "ドメイン (年額)",    "monthly_cost": 100,   "category": "software"},
    {"name": "サーバー/ホスティング", "monthly_cost": 1000, "category": "software"},
    {"name": "Adobe CC",           "monthly_cost": 7000,  "category": "software"},
]


def load_subscriptions() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"subscriptions": [], "meta": {"version": "4.6"}}


def save_subscriptions(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_subscription(
    name: str,
    monthly_cost: int,
    billing_day: int = 1,
    active: bool = True,
    renewal_date: str = "",
    memo: str = "",
) -> dict:
    data = load_subscriptions()
    now = datetime.now().isoformat(timespec="seconds")
    sub = {
        "subscription_id": "sub_" + uuid.uuid4().hex[:8],
        "name":            name,
        "monthly_cost":    monthly_cost,
        "billing_day":     billing_day,
        "active":          active,
        "renewal_date":    renewal_date,
        "memo":            memo,
        "created_at":      now,
        "updated_at":      now,
    }
    data["subscriptions"].append(sub)
    save_subscriptions(data)
    return sub


def update_subscription(sub_id: str, **kwargs) -> dict | None:
    data = load_subscriptions()
    for sub in data["subscriptions"]:
        if sub["subscription_id"] == sub_id:
            for k, v in kwargs.items():
                sub[k] = v
            sub["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_subscriptions(data)
            return sub
    return None


def toggle_active(sub_id: str) -> bool | None:
    data = load_subscriptions()
    for sub in data["subscriptions"]:
        if sub["subscription_id"] == sub_id:
            sub["active"] = not sub.get("active", True)
            sub["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_subscriptions(data)
            return sub["active"]
    return None


def delete_subscription(sub_id: str) -> bool:
    data = load_subscriptions()
    before = len(data["subscriptions"])
    data["subscriptions"] = [s for s in data["subscriptions"] if s["subscription_id"] != sub_id]
    if len(data["subscriptions"]) < before:
        save_subscriptions(data)
        return True
    return False


def get_monthly_subscription_total(data: dict) -> int:
    return sum(
        s.get("monthly_cost", 0)
        for s in data.get("subscriptions", [])
        if s.get("active", True)
    )


def get_upcoming_renewals(data: dict, days: int = 7) -> list[dict]:
    today = date.today()
    result = []
    for sub in data.get("subscriptions", []):
        if not sub.get("active", True):
            continue
        renewal = sub.get("renewal_date", "")
        if not renewal:
            continue
        try:
            rd = date.fromisoformat(renewal)
            diff = (rd - today).days
            if 0 <= diff <= days:
                result.append({**sub, "_days_until_renewal": diff})
        except Exception:
            pass
    return sorted(result, key=lambda s: s.get("renewal_date", ""))


def get_factory_summary(data: dict) -> dict:
    subs = data.get("subscriptions", [])
    active = [s for s in subs if s.get("active", True)]
    return {
        "total_subscriptions": len(subs),
        "active_subscriptions": len(active),
        "monthly_total":        get_monthly_subscription_total(data),
        "upcoming_renewals":    len(get_upcoming_renewals(data, 7)),
    }
