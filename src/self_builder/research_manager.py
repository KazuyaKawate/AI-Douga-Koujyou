from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from src.core.development_constitution import score_improvement
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge


RESEARCH_AGENTS = [
    "Official Docs Agent",
    "GitHub Agent",
    "Library Agent",
    "AI Model Agent",
    "Security Agent",
    "UI/UX Agent",
    "SEO Agent",
    "Market Agent",
    "Business Agent",
    "Community Agent",
]

AGENT_PROFILES = {
    "Official Docs Agent": ("official_docs", "公式ドキュメント", 0.95, "high"),
    "GitHub Agent": ("github", "GitHub Releases / Issues", 0.82, "medium"),
    "Library Agent": ("library", "ライブラリ更新情報", 0.78, "medium"),
    "AI Model Agent": ("ai_model", "AIモデル仕様", 0.86, "high"),
    "Security Agent": ("security", "セキュリティ通知", 0.9, "high"),
    "UI/UX Agent": ("ui_ux", "UI/UX事例", 0.76, "medium"),
    "SEO Agent": ("seo", "検索エンジン更新", 0.8, "medium"),
    "Market Agent": ("market", "市場トレンド", 0.72, "medium"),
    "Business Agent": ("business", "収益化事例", 0.74, "medium"),
    "Community Agent": ("community", "コミュニティ知見", 0.68, "low"),
}

SOURCE_PRIORITY = {
    "公式ドキュメント": 1.0,
    "セキュリティ通知": 0.96,
    "AIモデル仕様": 0.92,
    "GitHub Releases / Issues": 0.84,
    "ライブラリ更新情報": 0.8,
    "検索エンジン更新": 0.78,
    "UI/UX事例": 0.74,
    "収益化事例": 0.72,
    "市場トレンド": 0.68,
    "コミュニティ知見": 0.62,
}

IMPACT_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4, "unknown": 0.2}
DEFAULT_RESEARCH_INTERVAL_DAYS = 7


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _summary(agent: str, topic: str) -> str:
    category, _, _, _ = AGENT_PROFILES[agent]
    return f"{topic or 'AIOS'} に関する {category} の更新候補を確認"


def source_priority(source: str) -> float:
    return SOURCE_PRIORITY.get(source, 0.5)


def research_score(confidence: float, impact_level: str, source: str, age_days: int = 0) -> float:
    priority = source_priority(source)
    impact = IMPACT_WEIGHT.get(impact_level, 0.2)
    aging_penalty = min(age_days * 0.03, 0.45)
    return round(max((confidence * 0.45) + (priority * 0.3) + (impact * 0.25) - aging_penalty, 0), 3)


def knowledge_age(result: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now()
    fetched = _parse_time(str(result.get("fetched_at", ""))) or current
    age_days = max((current - fetched).days, 0)
    score = research_score(
        float(result.get("confidence", 0)),
        str(result.get("impact_level", "unknown")),
        str(result.get("source", "")),
        age_days,
    )
    return {
        "age_days": age_days,
        "is_stale": age_days >= DEFAULT_RESEARCH_INTERVAL_DAYS or score < 0.55,
        "aged_score": score,
    }


def research_scheduler() -> dict[str, Any]:
    knowledge = load_knowledge()
    schedule = knowledge.get("research_schedule", {})
    now = datetime.now()
    due_agents = []
    next_runs = {}
    for agent in RESEARCH_AGENTS:
        last_run = _parse_time(str(schedule.get(agent, {}).get("last_run", "")))
        next_run = last_run + timedelta(days=DEFAULT_RESEARCH_INTERVAL_DAYS) if last_run else now
        next_runs[agent] = next_run.isoformat(timespec="seconds")
        if next_run <= now:
            due_agents.append(agent)
    return {
        "due_agents": due_agents,
        "next_runs": next_runs,
        "interval_days": DEFAULT_RESEARCH_INTERVAL_DAYS,
    }


def conflict_resolver(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_category: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_category.setdefault(str(result.get("category", "")), []).append(result)
    conflicts = []
    resolved = []
    for category, items in by_category.items():
        ranked = sorted(items, key=lambda item: item.get("research_score", 0), reverse=True)
        resolved.extend(ranked)
        if len(items) > 1 and ranked[0].get("update_summary") != ranked[-1].get("update_summary"):
            conflicts.append(
                {
                    "category": category,
                    "winner": ranked[0].get("research_id", ""),
                    "candidates": [item.get("research_id", "") for item in ranked],
                    "reason": "research_scoreが高い情報を優先",
                }
            )
    return {"resolved": resolved, "conflicts": conflicts}


def run_research_team(topic: str = "AIOS Self Builder") -> list[dict[str, Any]]:
    fetched_at = _now()
    results = []
    for agent in RESEARCH_AGENTS:
        category, source, confidence, impact = AGENT_PROFILES[agent]
        results.append(
            {
                "research_id": f"rs-{uuid4().hex[:10]}",
                "agent": agent,
                "status": "done",
                "fetched_at": fetched_at,
                "source": source,
                "confidence": confidence,
                "source_priority": source_priority(source),
                "category": category,
                "tags": [category, "self_builder", "research_team"],
                "update_summary": _summary(agent, topic),
                "impact_level": impact,
                "aios_impact": f"{agent} の観点でAIOS改善余地を評価",
                "improvement_suggestion": f"{category} の知見をMission Plannerの制約と確認項目へ反映",
                "research_score": research_score(confidence, impact, source),
                "opportunity_report": opportunity_report(category, topic, confidence, impact),
                "age_days": 0,
                "is_stale": False,
            }
        )
    save_research_results(results)
    return results


def save_research_results(results: list[dict[str, Any]]) -> None:
    knowledge = load_knowledge()
    resolved = conflict_resolver(results)
    for result in resolved["resolved"]:
        aging = knowledge_age(result)
        result["age_days"] = aging["age_days"]
        result["is_stale"] = aging["is_stale"]
        result["research_score"] = aging["aged_score"]
        knowledge["research_results"].insert(0, result)
        category = result["category"]
        knowledge["categories"].setdefault(category, [])
        knowledge["categories"][category].insert(0, result["research_id"])
        for tag in result.get("tags", []):
            knowledge["tags"].setdefault(tag, [])
            knowledge["tags"][tag].insert(0, result["research_id"])
        knowledge["timeline"].insert(
            0,
            {
                "research_id": result["research_id"],
                "agent": result["agent"],
                "category": category,
                "fetched_at": result["fetched_at"],
                "impact_level": result["impact_level"],
                "research_score": result["research_score"],
            },
        )
        knowledge["research_schedule"][result["agent"]] = {
            "last_run": result["fetched_at"],
            "next_run": (datetime.fromisoformat(result["fetched_at"]) + timedelta(days=DEFAULT_RESEARCH_INTERVAL_DAYS)).isoformat(timespec="seconds"),
        }
    knowledge["conflicts"] = resolved["conflicts"] + knowledge.get("conflicts", [])
    save_knowledge(knowledge)


def research_dashboard() -> dict[str, Any]:
    knowledge = load_knowledge()
    results = knowledge.get("research_results", [])
    latest_by_agent = {}
    for result in results:
        latest_by_agent.setdefault(result.get("agent", ""), result)
    states = [
        {
            "agent": agent,
            "status": latest_by_agent.get(agent, {}).get("status", "waiting"),
            "latest": latest_by_agent.get(agent, {}).get("update_summary", "未調査"),
            "confidence": latest_by_agent.get(agent, {}).get("confidence", 0),
            "impact_level": latest_by_agent.get(agent, {}).get("impact_level", "unknown"),
        }
        for agent in RESEARCH_AGENTS
    ]
    high_impact = [item for item in results if item.get("impact_level") == "high"]
    stale = [item for item in results if knowledge_age(item)["is_stale"]]
    latest_update = results[0] if results else {}
    scheduler = research_scheduler()
    return {
        "agent_states": states,
        "latest_results": results[:10],
        "update_count": len(results),
        "high_impact_count": len(high_impact),
        "average_confidence": round(sum(item.get("confidence", 0) for item in results[:10]) / max(len(results[:10]), 1), 2),
        "latest_update": latest_update,
        "important_updates": sorted(high_impact, key=lambda item: item.get("research_score", 0), reverse=True)[:5],
        "revisit_targets": stale[:5],
        "due_agents": scheduler["due_agents"],
        "next_runs": scheduler["next_runs"],
        "suggestions": [item.get("improvement_suggestion", "") for item in high_impact[:5]],
    }


def notify_mission_planner() -> dict[str, Any]:
    dashboard = research_dashboard()
    suggestions = dashboard["suggestions"]
    return {
        "has_impact": bool(suggestions),
        "message": "Research結果により改善タスク候補があります" if suggestions else "Mission Plannerへ通知する高影響の更新はありません",
        "suggestions": suggestions,
        "opportunity_reports": [item.get("opportunity_report", {}) for item in dashboard.get("important_updates", [])],
    }


def opportunity_report(category: str, topic: str, confidence: float, impact_level: str) -> dict[str, Any]:
    scored = score_improvement(
        {
            "instruction": f"{topic} {category} opportunity",
            "estimated_revenue": 16000 if category in ("seo", "market", "business") else 5000,
            "risk": "low" if confidence >= 0.8 else "medium",
            "effort": 20 if impact_level == "high" else 35,
        }
    )
    return {
        "search_demand": "monitor",
        "competition": "monitor",
        "market": category,
        "profitability": scored["profitability"],
        "roi_score": scored["roi_score"],
        "recommendation": "Mission Plannerへ収益候補として通知" if scored["constitution_priority_score"] >= 30 else "継続監視",
    }


def research_improvement_candidates() -> list[dict[str, Any]]:
    notification = notify_mission_planner()
    candidates = []
    for suggestion in notification["suggestions"]:
        candidates.append(
            {
                "instruction": f"Research Teamの提案を反映する: {suggestion}",
                "plan": "Pro Plan",
                "target_files": ["pages/35_Self_Builder.py", "src/self_builder/"],
            }
        )
    for item in research_dashboard()["revisit_targets"]:
        candidates.append(
            {
                "instruction": f"再調査対象を更新する: {item.get('category')} / {item.get('update_summary')}",
                "plan": "Free Plan",
                "target_files": ["src/self_builder/research_manager.py"],
            }
        )
    return candidates
