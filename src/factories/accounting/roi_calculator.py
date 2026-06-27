"""ROI calculator — rule-based profitability metrics. No external API."""
from datetime import date
from pathlib import Path


def load_settings() -> dict:
    settings_path = Path(__file__).parent.parent.parent.parent / "config" / "accounting_settings.json"
    if settings_path.exists():
        try:
            import json
            return json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"break_even_monthly": 50000, "large_expense_threshold": 10000, "high_subscription_ratio": 30}


def calculate_roi(
    revenue_data: dict,
    expense_data: dict,
    subscription_data: dict,
    year_month: str = "",
) -> dict:
    from src.factories.accounting.revenue_manager import get_monthly_revenue, get_revenue_by_factory
    from src.factories.accounting.expense_manager import get_monthly_expenses, get_expenses_by_category
    from src.factories.accounting.subscription_manager import get_monthly_subscription_total

    if not year_month:
        year_month = date.today().strftime("%Y-%m")

    settings = load_settings()
    break_even = settings.get("break_even_monthly", 50000)

    total_revenue = get_monthly_revenue(revenue_data, year_month)
    expense_paid  = get_monthly_expenses(expense_data, year_month)
    sub_cost      = get_monthly_subscription_total(subscription_data)
    total_expense = expense_paid + sub_cost
    net_profit    = total_revenue - total_expense

    roi = round((net_profit / total_expense * 100), 1) if total_expense > 0 else 0.0
    break_even_remaining = max(0, break_even - total_revenue)
    target_attainment = round((total_revenue / break_even * 100), 1) if break_even > 0 else 0.0

    revenue_by_factory = get_revenue_by_factory(revenue_data, year_month)
    expense_by_category = get_expenses_by_category(expense_data, year_month)

    return {
        "year_month":          year_month,
        "total_revenue":       total_revenue,
        "expense_paid":        expense_paid,
        "sub_cost":            sub_cost,
        "total_expense":       total_expense,
        "net_profit":          net_profit,
        "roi":                 roi,
        "break_even_target":   break_even,
        "break_even_remaining": break_even_remaining,
        "target_attainment":   target_attainment,
        "revenue_by_factory":  revenue_by_factory,
        "expense_by_category": expense_by_category,
        "is_profitable":       net_profit >= 0,
    }


def get_cost_per_factory(expense_data: dict, subscription_data: dict, year_month: str = "") -> dict:
    from src.factories.accounting.expense_manager import get_monthly_expenses
    from src.factories.accounting.subscription_manager import get_monthly_subscription_total
    if not year_month:
        year_month = date.today().strftime("%Y-%m")
    total = get_monthly_expenses(expense_data, year_month) + get_monthly_subscription_total(subscription_data)
    return {"共通コスト": total}
