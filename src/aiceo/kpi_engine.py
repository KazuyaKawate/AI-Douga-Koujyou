"""kpi_engine — KPI achievement analysis for AI CEO Core."""
from __future__ import annotations


def analyze_kpi(snap: dict) -> dict:
    kpi = snap.get("kpi", {})
    rows = kpi.get("rows", [])
    if not rows:
        return {"available": False, "avg_pct": 0, "alerts": [], "summary": []}

    actuals = [r for r in rows if r.get("is_actual")]
    avg_pct = int(sum(r["pct"] for r in actuals) / len(actuals)) if actuals else 0

    alerts: list[str] = []
    summary: list[dict] = []
    for r in actuals:
        pct = r["pct"]
        label = r["label"]
        status = "ok" if pct >= 80 else ("warn" if pct >= 40 else "low")
        icon = "✅" if status == "ok" else ("⚠️" if status == "warn" else "🔴")
        summary.append({
            "key": r["key"],
            "label": label,
            "actual": r["actual"],
            "target": r["target"],
            "pct": pct,
            "unit": r["unit"],
            "status": status,
            "icon": icon,
        })
        if status == "low":
            alerts.append(f"🔴 {label}: {pct}% (actual {r['actual']:,} / target {r['target']:,} {r['unit']})")
        elif status == "warn":
            alerts.append(f"⚠️ {label}: {pct}%")

    revenue_row = next((r for r in summary if r["key"] == "sales_actual"), None)
    revenue_pct = revenue_row["pct"] if revenue_row else 0

    return {
        "available": True,
        "avg_pct": avg_pct,
        "revenue_pct": revenue_pct,
        "alerts": alerts,
        "summary": summary,
        "health": "ok" if avg_pct >= 70 else ("warn" if avg_pct >= 40 else "low"),
    }
