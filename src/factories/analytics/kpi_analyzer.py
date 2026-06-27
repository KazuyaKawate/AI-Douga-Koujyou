"""kpi_analyzer — analyze KPI achievement from kpi_targets.json."""
from __future__ import annotations

KPI_LABELS: dict[str, str] = {
    "revenue":     "売上",
    "note_posts":  "note投稿数",
    "video_count": "動画制作数",
    "sns_posts":   "SNS投稿数",
    "sales_calls": "営業件数",
    "dev_commits": "開発コミット",
    "study_hours": "学習時間",
}

KPI_UNITS: dict[str, str] = {
    "revenue": "円",
}


def analyze_kpi(kpi_data: dict) -> dict:
    """Analyze KPI targets vs actuals. Return structured result."""
    targets = kpi_data.get("targets", {})
    actuals = kpi_data.get("actuals", {})
    rows = []
    for key, target in targets.items():
        if not isinstance(target, (int, float)) or target == 0:
            continue
        actual = actuals.get(key, 0)
        pct = round(actual / target * 100)
        rows.append({
            "key":      key,
            "label":    KPI_LABELS.get(key, key),
            "unit":     KPI_UNITS.get(key, ""),
            "target":   target,
            "actual":   actual,
            "pct":      pct,
            "achieved": pct >= 100,
        })
    achieved    = sum(1 for r in rows if r["achieved"])
    avg_pct     = round(sum(r["pct"] for r in rows) / len(rows)) if rows else 0
    below_50    = [r for r in rows if r["pct"] < 50]
    return {
        "rows":     rows,
        "total":    len(rows),
        "achieved": achieved,
        "avg_pct":  avg_pct,
        "below_50": below_50,
        "at_100":   [r for r in rows if r["achieved"]],
        "date":     kpi_data.get("date", ""),
    }


def get_kpi_insights(analysis: dict) -> list[str]:
    """Return rule-based KPI insight strings."""
    insights: list[str] = []
    avg = analysis["avg_pct"]
    if not analysis["rows"]:
        return ["📊 KPIデータがまだありません。Mission Controlで目標を設定してください。"]
    if avg >= 80:
        insights.append(f"✅ KPI平均達成率 {avg}% — 好調です")
    elif avg >= 50:
        insights.append(f"📊 KPI平均達成率 {avg}% — 改善の余地があります")
    else:
        insights.append(f"⚠️ KPI平均達成率 {avg}% — 優先度を見直してください")
    for r in analysis["below_50"]:
        insights.append(f"🔴 {r['label']} が目標の {r['pct']}% — 要対応")
    for r in analysis["at_100"]:
        insights.append(f"✅ {r['label']} 目標達成!")
    if analysis["achieved"] == analysis["total"] and analysis["total"] > 0:
        insights.append("🏆 全KPI達成! 素晴らしいパフォーマンスです")
    return insights
