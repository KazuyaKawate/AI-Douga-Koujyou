"""Expense manager — CRUD for expense entries with category tracking."""
import json
import uuid
from datetime import date, datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "accounting_expenses.json"

EXPENSE_CATEGORIES = [
    "AI subscription", "API", "design", "software",
    "marketing", "outsourcing", "office", "other",
]

CATEGORY_LABELS = {
    "AI subscription": "🤖 AIサブスク",
    "API":             "⚙️ API費用",
    "design":          "🎨 デザイン",
    "software":        "💻 ソフトウェア",
    "marketing":       "📣 マーケティング",
    "outsourcing":     "👥 外注",
    "office":          "🏢 オフィス",
    "other":           "🔹 その他",
}

BILLING_CYCLES = ["monthly", "yearly", "one-time"]
BILLING_LABELS = {"monthly": "月額", "yearly": "年額", "one-time": "単発"}

EXPENSE_STATUSES = ["paid", "pending", "cancelled"]
STATUS_LABELS = {"paid": "✅ 支払済", "pending": "⏳ 未払い", "cancelled": "❌ キャンセル"}


def load_expenses() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"expenses": [], "meta": {"version": "4.6"}}


def save_expenses(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_expense(
    category: str,
    service_name: str,
    amount: int,
    billing_cycle: str = "monthly",
    entry_date: str = "",
    status: str = "paid",
    memo: str = "",
) -> dict:
    data = load_expenses()
    now = datetime.now().isoformat(timespec="seconds")
    if not entry_date:
        entry_date = date.today().isoformat()
    exp = {
        "expense_id":    "exp_" + uuid.uuid4().hex[:8],
        "category":      category,
        "service_name":  service_name,
        "amount":        amount,
        "billing_cycle": billing_cycle,
        "date":          entry_date,
        "status":        status,
        "memo":          memo,
        "created_at":    now,
        "updated_at":    now,
    }
    data["expenses"].append(exp)
    save_expenses(data)
    return exp


def update_expense(expense_id: str, **kwargs) -> dict | None:
    data = load_expenses()
    for exp in data["expenses"]:
        if exp["expense_id"] == expense_id:
            for k, v in kwargs.items():
                exp[k] = v
            exp["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_expenses(data)
            return exp
    return None


def delete_expense(expense_id: str) -> bool:
    data = load_expenses()
    before = len(data["expenses"])
    data["expenses"] = [e for e in data["expenses"] if e["expense_id"] != expense_id]
    if len(data["expenses"]) < before:
        save_expenses(data)
        return True
    return False


def get_monthly_expenses(data: dict, year_month: str = "") -> int:
    if not year_month:
        year_month = date.today().strftime("%Y-%m")
    return sum(
        e["amount"] for e in data.get("expenses", [])
        if e.get("date", "")[:7] == year_month and e.get("status") == "paid"
    )


def get_expenses_by_category(data: dict, year_month: str = "") -> dict:
    if not year_month:
        year_month = date.today().strftime("%Y-%m")
    result: dict[str, int] = {}
    for e in data.get("expenses", []):
        if e.get("date", "")[:7] == year_month and e.get("status") == "paid":
            cat = e.get("category", "other")
            result[cat] = result.get(cat, 0) + e.get("amount", 0)
    return result


def get_factory_summary(data: dict) -> dict:
    year_month = date.today().strftime("%Y-%m")
    return {
        "month_expense":  get_monthly_expenses(data, year_month),
        "total_entries":  len(data.get("expenses", [])),
        "paid_count":     sum(1 for e in data.get("expenses", []) if e.get("status") == "paid"),
        "pending_count":  sum(1 for e in data.get("expenses", []) if e.get("status") == "pending"),
        "by_category":    get_expenses_by_category(data, year_month),
    }
