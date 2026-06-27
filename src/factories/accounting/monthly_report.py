"""Monthly report generator — export accounting summary to reports/monthly/."""
from datetime import date
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent.parent.parent / "reports" / "monthly"


def generate_monthly_report(
    year_month: str,
    revenue_data: dict,
    expense_data: dict,
    subscription_data: dict,
    roi: dict,
    warnings: list[dict],
) -> str:
    from src.factories.accounting.revenue_manager import (
        get_monthly_revenue, get_revenue_by_source, SOURCE_LABELS,
    )
    from src.factories.accounting.expense_manager import (
        get_monthly_expenses, get_expenses_by_category, CATEGORY_LABELS,
    )
    from src.factories.accounting.subscription_manager import get_monthly_subscription_total
    from src.factories.accounting.audit_checker import AUDIT_LEVELS

    yr, mo = year_month.split("-")
    title = f"{yr}年{int(mo):d}月"

    revenue = get_monthly_revenue(revenue_data, year_month)
    expense = get_monthly_expenses(expense_data, year_month)
    sub_cost = get_monthly_subscription_total(subscription_data)
    total_expense = expense + sub_cost
    net_profit = revenue - total_expense

    by_source = get_revenue_by_source(revenue_data, year_month)
    by_category = get_expenses_by_category(expense_data, year_month)
    subs = subscription_data.get("subscriptions", [])
    active_subs = [s for s in subs if s.get("active", True)]

    lines = [
        f"# 会計監査レポート — {title}",
        f"> 生成日: {date.today().isoformat()}",
        "",
        "---",
        "",
        "## 収入サマリー",
        "",
        f"| 項目 | 金額 |",
        f"|------|------|",
        f"| **今月売上合計** | ¥{revenue:,} |",
    ]
    for src, amt in sorted(by_source.items(), key=lambda x: -x[1]):
        label = SOURCE_LABELS.get(src, src)
        lines.append(f"| {label} | ¥{amt:,} |")
    lines += ["", "---", "", "## 経費サマリー", ""]
    lines += [
        "| 項目 | 金額 |",
        "|------|------|",
        f"| **今月経費合計** | ¥{expense:,} |",
    ]
    for cat, amt in sorted(by_category.items(), key=lambda x: -x[1]):
        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(f"| {label} | ¥{amt:,} |")
    lines += ["", "---", "", "## サブスク費用", ""]
    lines += [
        "| サービス | 月額 | 状態 |",
        "|---------|------|------|",
    ]
    for sub in active_subs:
        lines.append(f"| {sub['name']} | ¥{sub.get('monthly_cost',0):,} | 稼働中 |")
    lines.append(f"| **合計** | ¥{sub_cost:,} | |")

    lines += ["", "---", "", "## 利益サマリー", ""]
    roi_pct = roi.get("roi", 0.0)
    lines += [
        "| 指標 | 値 |",
        "|------|---|",
        f"| 売上 | ¥{revenue:,} |",
        f"| 経費合計 | ¥{total_expense:,} |",
        f"| **純利益** | ¥{net_profit:,} |",
        f"| ROI | {roi_pct}% |",
        f"| 損益分岐点 | ¥{roi.get('break_even_target',0):,} |",
        f"| 達成率 | {roi.get('target_attainment',0)}% |",
    ]

    lines += ["", "---", "", "## 監査アラート", ""]
    if not warnings:
        lines.append("✅ 今月の監査アラートはありません。")
    else:
        for w in warnings:
            level_info = AUDIT_LEVELS.get(w.get("level", "info"), {"icon": "🔹"})
            icon = level_info["icon"]
            lines.append(f"- {icon} **{w.get('message','')}**")
            if w.get("details"):
                lines.append(f"  - {w['details']}")

    lines += ["", "---", "", "## 来月の推奨アクション", ""]
    recommendations = _generate_recommendations(revenue, total_expense, net_profit, warnings, roi)
    for i, rec in enumerate(recommendations, 1):
        lines.append(f"{i}. {rec}")

    lines += ["", "---", "", f"*Creator Factory OS v4.6 — 会計監査工場*"]

    return "\n".join(lines)


def export_monthly_report(content: str, year_month: str = "") -> Path:
    if not year_month:
        year_month = date.today().strftime("%Y-%m")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{year_month}_accounting_report.md"
    out_path = REPORTS_DIR / filename
    out_path.write_text(content, encoding="utf-8")
    return out_path


def _generate_recommendations(
    revenue: int,
    total_expense: int,
    net_profit: int,
    warnings: list[dict],
    roi: dict,
) -> list[str]:
    recs = []
    warn_codes = {w.get("code") for w in warnings}

    if net_profit < 0:
        recs.append("経費削減: 使用頻度が低いサブスクリプションを見直してください")
    if "no_revenue_this_month" in warn_codes:
        recs.append("売上入力: 収入の記録を忘れずに入力してください")
    if "high_subscription_ratio" in warn_codes:
        recs.append("サブスク最適化: 費用対効果の低いサービスを停止または下位プランに変更してください")
    if revenue > 0 and total_expense > 0:
        target_next = int(revenue * 1.1)
        recs.append(f"売上目標: 来月は ¥{target_next:,} (今月比+10%) を目指しましょう")
    attain = roi.get("target_attainment", 0)
    if attain < 100 and roi.get("break_even_target", 0) > 0:
        remaining = roi.get("break_even_remaining", 0)
        recs.append(f"損益分岐点: あと ¥{remaining:,} の売上で達成できます")
    if not recs:
        recs.append("好調です。現在のペースを維持してください")
    return recs
