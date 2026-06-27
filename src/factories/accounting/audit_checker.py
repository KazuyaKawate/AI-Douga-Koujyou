"""Audit checker — rule-based financial warnings. No external API."""
from datetime import date

AUDIT_LEVELS = {
    "error":   {"icon": "🔴", "label": "エラー"},
    "warning": {"icon": "🟠", "label": "警告"},
    "info":    {"icon": "🟡", "label": "情報"},
}


def check_audits(
    revenue_data: dict,
    expense_data: dict,
    subscription_data: dict,
    settings: dict | None = None,
) -> list[dict]:
    if settings is None:
        from src.factories.accounting.roi_calculator import load_settings
        settings = load_settings()

    from src.factories.accounting.revenue_manager import get_monthly_revenue
    from src.factories.accounting.expense_manager import get_monthly_expenses
    from src.factories.accounting.subscription_manager import get_monthly_subscription_total

    year_month = date.today().strftime("%Y-%m")
    break_even = settings.get("break_even_monthly", 50000)
    large_thresh = settings.get("large_expense_threshold", 10000)
    high_sub_ratio = settings.get("high_subscription_ratio", 30)

    total_revenue = get_monthly_revenue(revenue_data, year_month)
    total_expense = get_monthly_expenses(expense_data, year_month)
    sub_cost = get_monthly_subscription_total(subscription_data)
    all_expense = total_expense + sub_cost
    net_profit = total_revenue - all_expense

    warnings: list[dict] = []

    # 1. Expense > revenue
    if all_expense > 0 and total_revenue < all_expense:
        warnings.append({
            "level":   "error",
            "code":    "expense_exceeds_revenue",
            "message": "今月の経費が売上を上回っています",
            "details": f"売上 ¥{total_revenue:,} < 経費 ¥{all_expense:,}",
        })

    # 2. Negative profit
    if net_profit < 0:
        warnings.append({
            "level":   "error",
            "code":    "negative_profit",
            "message": f"今月の利益がマイナスです (¥{net_profit:,})",
            "details": "経費を削減するか売上を増やしてください",
        })

    # 3. No revenue this month
    revenue_entries = [
        r for r in revenue_data.get("revenue", [])
        if r.get("date", "")[:7] == year_month and r.get("status") == "confirmed"
    ]
    if not revenue_entries:
        warnings.append({
            "level":   "warning",
            "code":    "no_revenue_this_month",
            "message": "今月の売上がまだ記録されていません",
            "details": "収入管理タブから売上を入力してください",
        })

    # 4. Subscription cost ratio too high
    if total_revenue > 0 and sub_cost > 0:
        ratio = sub_cost / total_revenue * 100
        if ratio > high_sub_ratio:
            warnings.append({
                "level":   "warning",
                "code":    "high_subscription_ratio",
                "message": f"サブスク費用が売上の {ratio:.0f}% を占めています",
                "details": f"サブスク ¥{sub_cost:,} / 売上 ¥{total_revenue:,} (基準: {high_sub_ratio}%)",
            })

    # 5. Large expense without memo
    large_expenses = [
        e for e in expense_data.get("expenses", [])
        if e.get("amount", 0) >= large_thresh
        and e.get("date", "")[:7] == year_month
        and not e.get("memo", "").strip()
    ]
    for exp in large_expenses:
        warnings.append({
            "level":   "info",
            "code":    "large_expense_no_memo",
            "message": f"大きな経費 ¥{exp['amount']:,} にメモがありません",
            "details": f"サービス: {exp.get('service_name', '不明')}",
        })

    # 6. Below break-even
    if total_revenue > 0 and break_even > 0 and total_revenue < break_even:
        remaining = break_even - total_revenue
        pct = total_revenue / break_even * 100
        warnings.append({
            "level":   "info",
            "code":    "below_break_even",
            "message": f"損益分岐点まで ¥{remaining:,} 残っています ({pct:.0f}% 達成)",
            "details": f"目標: ¥{break_even:,} / 現在: ¥{total_revenue:,}",
        })

    return warnings


def get_audit_summary(warnings: list[dict]) -> dict:
    return {
        "total":   len(warnings),
        "errors":  sum(1 for w in warnings if w.get("level") == "error"),
        "warning": sum(1 for w in warnings if w.get("level") == "warning"),
        "info":    sum(1 for w in warnings if w.get("level") == "info"),
        "highest": "error" if any(w["level"] == "error" for w in warnings)
                   else "warning" if any(w["level"] == "warning" for w in warnings)
                   else "info" if warnings else "ok",
    }
