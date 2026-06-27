"""Revenue manager — CRUD for income entries with source factory tracking."""
import json
import uuid
from datetime import date, datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "accounting_revenue.json"

REVENUE_SOURCES = ["note", "sns", "video", "sales", "consulting", "affiliate", "template", "other"]

SOURCE_LABELS = {
    "note":       "📝 note",
    "sns":        "📱 SNS",
    "video":      "🎬 動画",
    "sales":      "💼 営業",
    "consulting": "🗣️ コンサル",
    "affiliate":  "🔗 アフィリエイト",
    "template":   "📄 テンプレ販売",
    "other":      "🔹 その他",
}

SOURCE_FACTORY_MAP = {
    "note":       "note投稿工場",
    "sns":        "SNS投稿工場",
    "video":      "AI動画工場",
    "sales":      "営業工場",
    "consulting": "営業工場",
    "affiliate":  "note投稿工場",
    "template":   "note投稿工場",
    "other":      "その他",
}

REVENUE_STATUSES = ["confirmed", "pending", "cancelled"]
STATUS_LABELS = {"confirmed": "✅ 確定", "pending": "⏳ 保留", "cancelled": "❌ キャンセル"}


def load_revenue() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"revenue": [], "meta": {"version": "4.6"}}


def save_revenue(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_revenue(
    source: str,
    amount: int,
    entry_date: str = "",
    source_factory: str = "",
    status: str = "confirmed",
    memo: str = "",
) -> dict:
    data = load_revenue()
    now = datetime.now().isoformat(timespec="seconds")
    if not entry_date:
        entry_date = date.today().isoformat()
    if not source_factory:
        source_factory = SOURCE_FACTORY_MAP.get(source, "その他")
    rev = {
        "revenue_id":      "rev_" + uuid.uuid4().hex[:8],
        "source":          source,
        "source_factory":  source_factory,
        "amount":          amount,
        "date":            entry_date,
        "status":          status,
        "memo":            memo,
        "created_at":      now,
        "updated_at":      now,
    }
    data["revenue"].append(rev)
    save_revenue(data)
    return rev


def update_revenue(revenue_id: str, **kwargs) -> dict | None:
    data = load_revenue()
    for rev in data["revenue"]:
        if rev["revenue_id"] == revenue_id:
            for k, v in kwargs.items():
                rev[k] = v
            rev["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_revenue(data)
            return rev
    return None


def delete_revenue(revenue_id: str) -> bool:
    data = load_revenue()
    before = len(data["revenue"])
    data["revenue"] = [r for r in data["revenue"] if r["revenue_id"] != revenue_id]
    if len(data["revenue"]) < before:
        save_revenue(data)
        return True
    return False


def get_today_revenue(data: dict) -> int:
    today = date.today().isoformat()
    return sum(
        r["amount"] for r in data.get("revenue", [])
        if r.get("date") == today and r.get("status") == "confirmed"
    )


def get_monthly_revenue(data: dict, year_month: str = "") -> int:
    if not year_month:
        year_month = date.today().strftime("%Y-%m")
    return sum(
        r["amount"] for r in data.get("revenue", [])
        if r.get("date", "")[:7] == year_month and r.get("status") == "confirmed"
    )


def get_revenue_by_source(data: dict, year_month: str = "") -> dict:
    if not year_month:
        year_month = date.today().strftime("%Y-%m")
    result: dict[str, int] = {}
    for r in data.get("revenue", []):
        if r.get("date", "")[:7] == year_month and r.get("status") == "confirmed":
            src = r.get("source", "other")
            result[src] = result.get(src, 0) + r.get("amount", 0)
    return result


def get_revenue_by_factory(data: dict, year_month: str = "") -> dict:
    if not year_month:
        year_month = date.today().strftime("%Y-%m")
    result: dict[str, int] = {}
    for r in data.get("revenue", []):
        if r.get("date", "")[:7] == year_month and r.get("status") == "confirmed":
            fac = r.get("source_factory", "その他")
            result[fac] = result.get(fac, 0) + r.get("amount", 0)
    return result


def get_factory_summary(data: dict) -> dict:
    today = date.today().isoformat()
    year_month = today[:7]
    return {
        "today_revenue":   get_today_revenue(data),
        "month_revenue":   get_monthly_revenue(data, year_month),
        "total_entries":   len(data.get("revenue", [])),
        "confirmed_count": sum(1 for r in data.get("revenue", []) if r.get("status") == "confirmed"),
        "pending_count":   sum(1 for r in data.get("revenue", []) if r.get("status") == "pending"),
    }
