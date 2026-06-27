"""roi_analyzer — cross-factory revenue, expense, profit and ROI analysis."""
from __future__ import annotations
from datetime import date


def analyze_roi(
    accounting_revenue: dict,
    accounting_expenses: dict,
    accounting_subscriptions: dict,
    sales_deals: dict,
    year_month: str = "",
) -> dict:
    """Calculate ROI metrics from Accounting and Sales config data."""
    ym = year_month or date.today().strftime("%Y-%m")

    # ── Revenue ───────────────────────────────────────────────────────────────
    revenues = accounting_revenue.get("revenue", [])
    month_revenue = sum(
        r.get("amount", 0) for r in revenues
        if r.get("entry_date", "")[:7] == ym and r.get("status") == "confirmed"
    )
    revenue_by_source: dict[str, int] = {}
    for r in revenues:
        if r.get("entry_date", "")[:7] == ym and r.get("status") == "confirmed":
            src = r.get("source_factory") or r.get("source", "other")
            revenue_by_source[src] = revenue_by_source.get(src, 0) + r.get("amount", 0)

    # ── Expenses ──────────────────────────────────────────────────────────────
    expenses = accounting_expenses.get("expenses", [])
    month_expense = sum(
        e.get("amount", 0) for e in expenses
        if e.get("entry_date", "")[:7] == ym and e.get("status") == "paid"
    )
    expense_by_category: dict[str, int] = {}
    for e in expenses:
        if e.get("entry_date", "")[:7] == ym and e.get("status") == "paid":
            cat = e.get("category", "other")
            expense_by_category[cat] = expense_by_category.get(cat, 0) + e.get("amount", 0)

    # ── Subscriptions ─────────────────────────────────────────────────────────
    subs = accounting_subscriptions.get("subscriptions", [])
    sub_cost = sum(s.get("monthly_cost", 0) for s in subs if s.get("active", True))
    active_subs = sum(1 for s in subs if s.get("active", True))

    # ── Sales contracted ──────────────────────────────────────────────────────
    deals = sales_deals.get("deals", [])
    sales_contracted = sum(
        d.get("amount", 0) for d in deals
        if d.get("stage") == "contracted" and d.get("updated_at", "")[:7] == ym
    )

    # ── Aggregates ────────────────────────────────────────────────────────────
    total_expense = month_expense + sub_cost
    net_profit    = month_revenue - total_expense
    roi           = round(net_profit / total_expense * 100, 1) if total_expense > 0 else 0.0
    sub_ratio     = round(sub_cost / month_revenue * 100) if month_revenue > 0 else 0

    return {
        "year_month":         ym,
        "total_revenue":      month_revenue,
        "sales_contracted":   sales_contracted,
        "month_expense":      month_expense,
        "sub_cost":           sub_cost,
        "active_subs":        active_subs,
        "total_expense":      total_expense,
        "net_profit":         net_profit,
        "roi":                roi,
        "sub_ratio":          sub_ratio,
        "revenue_by_source":  revenue_by_source,
        "expense_by_category":expense_by_category,
        "is_profitable":      net_profit > 0,
    }


def get_roi_insights(analysis: dict, roi_target: float = 20.0) -> list[str]:
    """Return rule-based ROI insight strings."""
    insights: list[str] = []
    if analysis["total_revenue"] == 0 and analysis["total_expense"] == 0:
        insights.append("📊 今月の収支データがまだありません")
        return insights
    if not analysis["is_profitable"] and analysis["total_expense"] > 0:
        insights.append(f"🔴 今月は赤字: ¥{abs(analysis['net_profit']):,} の損失")
    elif analysis["roi"] >= roi_target:
        insights.append(f"✅ ROI {analysis['roi']}% — 目標 ({roi_target}%) 達成")
    elif analysis["roi"] > 0:
        insights.append(f"📊 ROI {analysis['roi']}% — 黒字ですが目標 ({roi_target}%) 未達")
    if analysis["sub_ratio"] > 30:
        insights.append(f"⚠️ サブスク費用が売上の {analysis['sub_ratio']}% を占めています")
    if analysis["sales_contracted"] > 0:
        insights.append(f"💼 今月の成約売上: ¥{analysis['sales_contracted']:,}")
    top_src = max(analysis["revenue_by_source"], key=analysis["revenue_by_source"].get) \
              if analysis["revenue_by_source"] else None
    if top_src:
        insights.append(f"📈 最大収入源: {top_src} (¥{analysis['revenue_by_source'][top_src]:,})")
    return insights
