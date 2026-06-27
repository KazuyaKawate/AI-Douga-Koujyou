"""project_analyzer — analyze project progress and factory distribution."""
from __future__ import annotations

STATUS_ICONS = {"active": "🟢", "paused": "🟡", "completed": "✅", "archived": "⬜"}


def analyze_projects() -> dict:
    """Return project progress summary and factory usage distribution."""
    try:
        from src.core.project_manager import get_all_projects
        projects = get_all_projects()
    except Exception:
        return _empty()

    if not projects:
        return _empty()

    active  = [p for p in projects if p.status == "active"]
    summaries = [p.get_summary() for p in projects]
    total_revenue = sum(p.revenue for p in projects)
    avg_progress  = sum(p.progress for p in projects) / len(projects)

    factory_usage: dict[str, int] = {}
    for p in projects:
        for f in p.factories:
            factory_usage[f] = factory_usage.get(f, 0) + 1

    most_used = max(factory_usage, key=lambda k: factory_usage[k]) if factory_usage else "—"

    return {
        "total":          len(projects),
        "active":         len(active),
        "total_revenue":  total_revenue,
        "avg_progress":   round(avg_progress, 1),
        "summaries":      summaries,
        "factory_usage":  factory_usage,
        "most_used_factory": most_used,
    }


def _empty() -> dict:
    return {
        "total": 0, "active": 0, "total_revenue": 0,
        "avg_progress": 0.0, "summaries": [],
        "factory_usage": {}, "most_used_factory": "—",
    }


def get_project_insights(analysis: dict) -> list[str]:
    """Return rule-based project insight strings."""
    insights: list[str] = []
    if analysis["total"] == 0:
        return ["📊 プロジェクトが未作成です。Mission Controlでプロジェクトを作成してください。"]
    if analysis["avg_progress"] == 0.0:
        insights.append("📊 プロジェクト進捗を更新してください (0%)")
    elif analysis["avg_progress"] >= 80:
        insights.append(f"✅ 平均進捗 {analysis['avg_progress']}% — もうすぐ完了です")
    else:
        insights.append(f"📊 平均進捗: {analysis['avg_progress']}%")
    if analysis["active"] > 3:
        insights.append(f"⚠️ 並行稼働プロジェクトが {analysis['active']} 件 — 集中が分散する可能性があります")
    if analysis["most_used_factory"] != "—":
        insights.append(f"🏭 最多使用工場: {analysis['most_used_factory']}")
    if analysis["total_revenue"] > 0:
        insights.append(f"💰 プロジェクト合計売上: ¥{analysis['total_revenue']:,}")
    return insights
