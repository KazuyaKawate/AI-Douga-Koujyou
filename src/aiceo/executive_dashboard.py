"""executive_dashboard.py — Compute overall health and CEO brief for AI CEO Core."""
from __future__ import annotations
from datetime import date


def compute_overall_health(snap: dict, risks: list[dict]) -> dict:
    scores: list[int] = []

    # KPI score
    kpi_rows = [r for r in snap.get("kpi", {}).get("rows", []) if r.get("is_actual")]
    if kpi_rows:
        avg_kpi = sum(r["pct"] for r in kpi_rows) / len(kpi_rows)
        scores.append(int(avg_kpi))

    # Task score
    task_pct = snap.get("tasks", {}).get("stats", {}).get("pct", 0)
    if snap.get("tasks", {}).get("stats", {}).get("total", 0) > 0:
        scores.append(task_pct)

    # Factory health score
    anl_fac = snap.get("analytics", {}).get("factories", {})
    if anl_fac.get("health_pct") is not None:
        scores.append(anl_fac["health_pct"])

    reg = snap.get("registry", {}).get("factories", {})
    if reg.get("total", 0) > 0:
        h_pct = int(reg.get("healthy", 0) / reg["total"] * 100)
        scores.append(h_pct)

    # Financial health
    month = snap.get("finance", {}).get("month", {})
    rev = month.get("revenue", 0)
    exp = month.get("expense", 0)
    be  = month.get("breakeven", 50000)
    if exp > 0:
        if rev >= be:
            scores.append(100)
        elif rev >= exp:
            scores.append(70)
        else:
            scores.append(20)

    overall = int(sum(scores) / len(scores)) if scores else 50

    # Penalise for high risks
    high_risks = sum(1 for r in risks if r.get("severity") == "high")
    overall = max(0, overall - high_risks * 8)

    if overall >= 80:
        label, icon, color = "Healthy",   "✅", "green"
    elif overall >= 60:
        label, icon, color = "Stable",    "🟡", "yellow"
    elif overall >= 40:
        label, icon, color = "Attention", "🟠", "orange"
    else:
        label, icon, color = "Critical",  "🔴", "red"

    return {
        "score": overall,
        "label": label,
        "icon": icon,
        "color": color,
        "component_scores": scores,
        "high_risks": high_risks,
    }


def generate_ceo_brief(
    snap: dict,
    health: dict,
    risks: list[dict],
    opportunities: list[dict],
    recommendations: list[dict],
) -> str:
    today = date.today().strftime("%Y年%m月%d日")
    score = health["score"]
    label = health["label"]
    icon  = health["icon"]

    lines: list[str] = [f"**{today} — {icon} OS Health: {label} ({score}%)**"]

    # Top priority
    task_stats = snap.get("tasks", {}).get("stats", {})
    pct = task_stats.get("pct", 0)
    tot = task_stats.get("total", 0)
    if tot > 0:
        lines.append(f"今日のタスク進捗: {pct}% ({task_stats.get('done', 0)}/{tot} 完了)。")

    # Revenue
    month = snap.get("finance", {}).get("month", {})
    rev = month.get("revenue", 0)
    exp = month.get("expense", 0)
    be  = month.get("breakeven", 50000)
    if rev >= be:
        lines.append(f"今月の損益分岐点を達成 (¥{rev:,} / ¥{be:,})。")
    elif exp > 0 and rev < exp:
        lines.append(f"⚠️ 今月赤字: 売上 ¥{rev:,} < 費用 ¥{exp:,}。緊急対応が必要。")
    elif rev > 0:
        lines.append(f"今月売上 ¥{rev:,} / 損益分岐点 ¥{be:,} (残り ¥{max(0, be - rev):,})。")

    # Top risk
    if risks:
        top = risks[0]
        lines.append(f"最重要リスク: {top['icon']} {top['title']}。")

    # Top recommendation
    if recommendations:
        top_rec = recommendations[0]
        lines.append(f"推奨アクション: **{top_rec['title']}**")

    return " ".join(lines)
