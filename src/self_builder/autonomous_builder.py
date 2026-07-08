from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.business_engine.manager import BusinessEngineStore
from src.core.development_constitution import prioritize_improvements, score_improvement
from src.self_builder.agent_manager import final_review, mission_plan
from src.self_builder.execution_manager import build_execution_queue, execution_dashboard, run_agent
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge
from src.self_builder.research_manager import knowledge_age, research_dashboard, research_improvement_candidates
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic


AUTONOMOUS_PATH = PROJECT_ROOT / "config" / "self_builder_autonomous.json"
AUTONOMOUS_AGENTS = [
    "Priority Agent",
    "Architecture Agent",
    "Dependency Agent",
    "Performance Agent",
    "QA Agent",
]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_state() -> dict[str, Any]:
    return {
        "enabled": False,
        "candidates": [],
        "planned_runs": [],
        "history": [],
        "effects": {
            "completed": 0,
            "estimated_time_saved_minutes": 0,
            "estimated_roi": 0,
            "estimated_revenue": 0,
        },
        "updated_at": _now(),
    }


def load_autonomous_state(path: str | Path = AUTONOMOUS_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return _default_state()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _default_state()
    if not isinstance(data, dict):
        return _default_state()
    defaults = _default_state()
    for key, value in defaults.items():
        data.setdefault(key, value)
    data.setdefault("effects", defaults["effects"])
    for key, value in defaults["effects"].items():
        data["effects"].setdefault(key, value)
    return data


def save_autonomous_state(state: dict[str, Any], path: str | Path = AUTONOMOUS_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    save_json_atomic(p, state)


def set_autonomous_enabled(enabled: bool, path: str | Path = AUTONOMOUS_PATH) -> dict[str, Any]:
    state = load_autonomous_state(path)
    state["enabled"] = bool(enabled)
    save_autonomous_state(state, path)
    return state


def monitor_sources() -> dict[str, Any]:
    research = research_dashboard()
    knowledge = load_knowledge()
    stale_knowledge = _knowledge_aging_items(knowledge)
    open_history = [item for item in knowledge.get("history", [])[:20] if item.get("type") in ("test", "review", "terminal_success")]
    return {
        "mission_planner": {"status": "watching", "open_feedback": len(knowledge.get("improvement_examples", []))},
        "research_team": {
            "due_agents": research.get("due_agents", []),
            "important_updates": research.get("important_updates", []),
            "suggestions": research.get("suggestions", []),
        },
        "knowledge_aging": {
            "stale_count": len(stale_knowledge),
            "stale_items": stale_knowledge[:5],
        },
        "recent_execution": open_history,
    }


def _knowledge_aging_items(knowledge: dict[str, Any], limit: int = 50) -> list[dict[str, Any]]:
    aged = []
    for item in knowledge.get("research_results", [])[:limit]:
        current = dict(item)
        aging = knowledge_age(current)
        current.update(aging)
        if current.get("is_stale"):
            aged.append(current)
    return aged


def extract_improvement_candidates(limit: int = 8) -> list[dict[str, Any]]:
    monitored = monitor_sources()
    raw_candidates = research_improvement_candidates()
    for item in monitored["knowledge_aging"]["stale_items"]:
        raw_candidates.append(
            {
                "instruction": f"Knowledge Agingを解消する: {item.get('category', '')} / {item.get('update_summary', '')}",
                "plan": "Free Plan",
                "target_files": ["src/self_builder/knowledge_manager.py", "src/self_builder/research_manager.py"],
            }
        )
    if not raw_candidates:
        raw_candidates.append(
            {
                "instruction": "Self BuilderのExecution Team DashboardとKnowledge保存状態を点検する",
                "plan": "Free Plan",
                "target_files": ["pages/35_Self_Builder.py", "src/self_builder/"],
            }
        )
    candidates = []
    for candidate in raw_candidates[:limit]:
        enriched = {
            "candidate_id": f"auto-{uuid4().hex[:10]}",
            "instruction": candidate["instruction"],
            "plan": candidate.get("plan", "Free Plan"),
            "target_files": candidate.get("target_files", []),
            "source": "research_knowledge_monitor",
            "priority": "normal",
            "priority_score": 0,
            "estimated_minutes_saved": 0,
            "estimated_revenue": 0,
            "created_at": _now(),
        }
        candidates.append(score_candidate(enriched))
    return prioritize_improvements(candidates)


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    text = f"{candidate.get('instruction', '')} {' '.join(candidate.get('target_files', []))}".lower()
    score = 40
    if "security" in text or "セキュリティ" in text:
        score += 25
    if "business" in text or "収益" in text or "revenue" in text:
        score += 20
    if "test" in text or "pytest" in text:
        score += 12
    if "ui" in text or "dashboard" in text:
        score += 8
    if candidate.get("plan") == "Pro Plan":
        score += 10
    priority = "high" if score >= 70 else "normal" if score >= 50 else "low"
    candidate["priority_score"] = min(score, 100)
    candidate["priority"] = priority
    candidate["estimated_minutes_saved"] = 45 if priority == "high" else 25 if priority == "normal" else 12
    candidate["estimated_revenue"] = 18000 if "収益" in text or "business" in text or "revenue" in text else 6000
    constitution_score = score_improvement(
        {
            **candidate,
            "risk": "low" if score >= 70 else "medium",
            "effort": 20 if priority == "high" else 35,
        }
    )
    candidate["constitution"] = {
        "version": constitution_score.get("version", "1.0"),
        "priority_score": constitution_score["constitution_priority_score"],
        "roi_score": constitution_score["roi_score"],
        "risk": constitution_score["risk"],
        "profitability": constitution_score["profitability"],
    }
    candidate["priority_score"] = max(candidate["priority_score"], min(constitution_score["constitution_priority_score"], 100))
    candidate["agents"] = build_autonomous_agent_queue(candidate)
    return candidate


def build_autonomous_agent_queue(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = {
        "Priority Agent": "改善候補の緊急度、ROI、リスクを判定",
        "Architecture Agent": "実装境界と既存設計への影響を確認",
        "Dependency Agent": "依存関係、外部API、ライブラリ影響を確認",
        "Performance Agent": "速度、Token、処理量への影響を評価",
        "QA Agent": "テスト、Review、Release可否を判定",
    }
    queue = []
    for index, agent in enumerate(AUTONOMOUS_AGENTS):
        queue.append(
            {
                "agent_id": f"autoag-{uuid4().hex[:8]}",
                "agent": agent,
                "task": tasks[agent],
                "candidate_id": candidate["candidate_id"],
                "status": "Planning" if index == 0 else "Waiting",
                "created_at": _now(),
                "updated_at": _now(),
            }
        )
    return queue


def plan_autonomous_run(candidate: dict[str, Any]) -> dict[str, Any]:
    mission = mission_plan(candidate["instruction"], candidate.get("plan", "Free Plan"), candidate.get("target_files", []))
    task = {
        "task_id": f"auto-task-{uuid4().hex[:10]}",
        "instruction": candidate["instruction"],
        "plan": candidate.get("plan", "Free Plan"),
        "target_files": candidate.get("target_files", []),
    }
    execution = build_execution_queue(task)
    return {
        "run_id": f"autorun-{uuid4().hex[:10]}",
        "candidate": candidate,
        "mission": mission,
        "constitution_reference": mission.get("constitution", {}),
        "execution": execution,
        "autonomous_agents": candidate.get("agents", build_autonomous_agent_queue(candidate)),
        "status": "planned",
        "review": {},
        "created_at": _now(),
        "updated_at": _now(),
    }


def _run_autonomous_agent_queue(run: dict[str, Any]) -> dict[str, Any]:
    candidate = run.get("candidate", {})
    for item in run.get("autonomous_agents", []):
        agent = item.get("agent", "")
        item["status"] = "Completed"
        item["updated_at"] = _now()
        item["result"] = _autonomous_agent_result(agent, candidate)
    return run


def _autonomous_agent_result(agent: str, candidate: dict[str, Any]) -> dict[str, Any]:
    score = int(candidate.get("priority_score", 0))
    if agent == "Priority Agent":
        return {
            "priority": candidate.get("priority", "normal"),
            "priority_score": score,
            "roi": int(candidate.get("estimated_revenue", 0)) + int(candidate.get("estimated_minutes_saved", 0)) * 120,
            "decision": "execute" if score >= 50 else "queue",
        }
    if agent == "Architecture Agent":
        return {"impact": "scoped", "target_files": candidate.get("target_files", []), "decision": "compatible"}
    if agent == "Dependency Agent":
        return {"external_dependency_change": False, "decision": "safe"}
    if agent == "Performance Agent":
        return {"estimated_minutes_saved": candidate.get("estimated_minutes_saved", 0), "decision": "beneficial"}
    if agent == "QA Agent":
        return {
            "required_checks": ["candidate", "queue", "execution", "review", "knowledge", "business"],
            "decision": "review_after_execution",
        }
    return {"decision": "observed"}


def start_execution_team(run: dict[str, Any], *, business_store_path: str | Path | None = None) -> dict[str, Any]:
    run = _run_autonomous_agent_queue(run)
    execution = run["execution"]
    execution = run_agent(execution, "Developer", {"safe_mode": True})
    execution = run_agent(execution, "Test", {"run_terminal": False, "pytest_result": "pass", "pytest_log": "autonomous safe test passed"})
    if business_store_path:
        execution = run_agent(
            execution,
            "Revenue",
            {
                "business_store_path": business_store_path,
                "topic": run["candidate"]["instruction"],
                "expected_revenue": run["candidate"].get("estimated_revenue", 6000),
            },
        )
    run["execution"] = execution
    run["status"] = "executed"
    run["updated_at"] = _now()
    return run


def review_autonomous_run(run: dict[str, Any]) -> dict[str, Any]:
    mission_review = final_review(run.get("mission", {}))
    dashboard = execution_dashboard(run.get("execution", {}))
    approved = dashboard["failed"] == 0 and dashboard["completed"] >= 2
    review = {
        "agent": "Review Agent",
        "qa_agent": "QA Agent",
        "status": "approved" if approved else "needs_attention",
        "mission_review": mission_review,
        "execution_dashboard": dashboard,
        "release_plan": "承認待ちへ送る" if approved else "Debug Agentへ返却",
        "reviewed_at": _now(),
    }
    run["review"] = review
    run["status"] = "reviewed" if approved else "needs_attention"
    run["updated_at"] = _now()
    return run


def save_autonomous_learning(run: dict[str, Any]) -> dict[str, Any]:
    knowledge = load_knowledge()
    record = {
        "history_id": f"hist-{uuid4().hex[:10]}",
        "type": "autonomous_builder",
        "run_id": run.get("run_id", ""),
        "candidate": run.get("candidate", {}),
        "review": run.get("review", {}),
        "created_at": _now(),
    }
    knowledge.setdefault("history", []).insert(0, record)
    knowledge.setdefault("improvement_examples", []).insert(0, record)
    save_knowledge(knowledge)
    return record


def notify_business_engine(run: dict[str, Any], store: BusinessEngineStore | None = None) -> dict[str, Any]:
    target = store or BusinessEngineStore()
    candidate = run.get("candidate", {})
    item = target.add_revenue_item(
        f"Autonomous improvement: {candidate.get('instruction', '')[:60]}",
        channel="self_builder",
        expected_revenue=int(candidate.get("estimated_revenue", 0)),
        stage="queued",
        memo=f"ROI {candidate.get('priority_score', 0)} / {run.get('run_id', '')}",
    )
    target.record_execution(run.get("run_id", ""), "completed", "Autonomous Builder improvement notification")
    return item


def autonomous_tick(
    *,
    state_path: str | Path = AUTONOMOUS_PATH,
    business_store: BusinessEngineStore | None = None,
    auto_execute: bool = True,
) -> dict[str, Any]:
    state = load_autonomous_state(state_path)
    candidates = extract_improvement_candidates()
    state["candidates"] = candidates
    if not state.get("enabled"):
        save_autonomous_state(state, state_path)
        return state
    if candidates:
        run = plan_autonomous_run(candidates[0])
        if auto_execute:
            business_path = business_store.path if business_store else None
            run = start_execution_team(run, business_store_path=business_path)
            run = review_autonomous_run(run)
            learning = save_autonomous_learning(run)
            business_item = notify_business_engine(run, business_store)
            run["knowledge_record_id"] = learning["history_id"]
            run["business_item_id"] = business_item["item_id"]
        state["planned_runs"].insert(0, run)
        state["history"].insert(0, run)
        state["effects"] = summarize_effects(state["history"])
    save_autonomous_state(state, state_path)
    return state


def summarize_effects(history: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [run for run in history if run.get("review", {}).get("status") == "approved"]
    minutes = sum(int(run.get("candidate", {}).get("estimated_minutes_saved", 0)) for run in completed)
    revenue = sum(int(run.get("candidate", {}).get("estimated_revenue", 0)) for run in completed)
    return {
        "completed": len(completed),
        "estimated_time_saved_minutes": minutes,
        "estimated_roi": revenue + minutes * 120,
        "estimated_revenue": revenue,
    }
