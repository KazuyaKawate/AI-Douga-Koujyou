"""priority_engine — Score and rank OS priorities for AI CEO Core.

Scoring: Impact(40%) + Urgency(30%) + ROI(20%) + Dependencies(10%) = 0-100
"""
from __future__ import annotations
from datetime import date

TODAY = date.today().isoformat()

_IMPACT_SCORE  = {"high": 100, "critical": 100, "medium": 60, "low": 30}
_STATUS_URGENCY = {"in_progress": 100, "blocked": 90, "planned": 50, "completed": 0, "archived": 0}
_TYPE_ROI = {"milestone": 100, "feature": 80, "bugfix": 70, "infra": 60, "refactor": 40, "docs": 20}
_PRIORITY_SCORE = {"critical": 100, "high": 80, "medium": 50, "low": 20}
_TASK_STATUS_URGENCY = {"in_progress": 100, "pending": 60, "done": 0}
_TASK_CAT_ROI = {
    "経営": 100, "会計監査工場": 90, "営業工場": 85,
    "AI動画工場": 80, "note投稿工場": 75, "SNS投稿工場": 70, "開発": 65,
}


def _score(impact: int, urgency: int, roi: int, dep_bonus: int = 0) -> float:
    return impact * 0.4 + urgency * 0.3 + roi * 0.2 + dep_bonus * 0.1


def score_priorities(snap: dict) -> list[dict]:
    items: list[dict] = []

    # ── Roadmap items ──────────────────────────────────────────────────────────
    try:
        from src.devstudio.roadmap_manager import get_all_items
        for rm in get_all_items():
            if rm.get("status") in ("completed", "archived"):
                continue
            impact   = _IMPACT_SCORE.get(rm.get("priority", "medium"), 60)
            urgency  = _STATUS_URGENCY.get(rm.get("status", "planned"), 50)
            roi      = _TYPE_ROI.get(rm.get("type", "feature"), 60)
            dep      = 20 if rm.get("status") == "blocked" else 0
            overdue  = 0
            if rm.get("planned_date") and rm["planned_date"] < TODAY and rm.get("status") != "completed":
                overdue = 20
            score = _score(impact, urgency + overdue, roi, dep)
            items.append({
                "source": "roadmap",
                "id": rm.get("roadmap_id", ""),
                "title": rm.get("title", ""),
                "status": rm.get("status", ""),
                "priority": rm.get("priority", ""),
                "score": round(score, 1),
                "version": rm.get("version", ""),
                "overdue": overdue > 0,
                "icon": "🗺️",
            })
    except Exception:
        pass

    # ── Tasks ─────────────────────────────────────────────────────────────────
    for task in snap.get("tasks", {}).get("tasks", []):
        if task.get("status") == "done":
            continue
        priority = task.get("priority", "medium")
        cat      = task.get("category", "開発")
        impact   = _PRIORITY_SCORE.get(priority, 50)
        urgency  = _TASK_STATUS_URGENCY.get(task.get("status", "pending"), 60)
        roi      = _TASK_CAT_ROI.get(cat, 60)
        score    = _score(impact, urgency, roi)
        items.append({
            "source": "task",
            "id": task.get("id", ""),
            "title": task.get("title", ""),
            "status": task.get("status", ""),
            "priority": priority,
            "score": round(score, 1),
            "category": cat,
            "overdue": False,
            "icon": "✅",
        })

    # ── Open high-impact decisions ────────────────────────────────────────────
    try:
        from src.devstudio.decision_log_manager import get_all_decisions
        for dec in get_all_decisions():
            if dec.get("status") != "open":
                continue
            impact  = _IMPACT_SCORE.get(dec.get("impact", "medium"), 60)
            urgency = 80
            roi     = 70
            score   = _score(impact, urgency, roi)
            items.append({
                "source": "decision",
                "id": dec.get("decision_id", ""),
                "title": f"Decide: {dec.get('theme', '')} — {dec.get('decision', '')[:50]}",
                "status": "open",
                "priority": dec.get("impact", "medium"),
                "score": round(score, 1),
                "overdue": False,
                "icon": "📋",
            })
    except Exception:
        pass

    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:10]
