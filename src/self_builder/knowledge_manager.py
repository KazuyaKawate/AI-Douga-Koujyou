from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic
from src.self_builder.agent_manager import load_agent_logs


KNOWLEDGE_PATH = PROJECT_ROOT / "config" / "self_builder_knowledge.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _empty_knowledge() -> dict[str, Any]:
    return {
        "success_examples": [],
        "failure_examples": [],
        "improvement_examples": [],
        "research_results": [],
        "categories": {},
        "tags": {},
        "timeline": [],
        "research_schedule": {},
        "conflicts": [],
        "development_constitution": {},
    }


def load_knowledge(path: str | Path = KNOWLEDGE_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return _empty_knowledge()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _empty_knowledge()
    if not isinstance(data, dict):
        return _empty_knowledge()
    data.setdefault("success_examples", [])
    data.setdefault("failure_examples", [])
    data.setdefault("improvement_examples", [])
    data.setdefault("research_results", [])
    data.setdefault("categories", {})
    data.setdefault("tags", {})
    data.setdefault("timeline", [])
    data.setdefault("research_schedule", {})
    data.setdefault("conflicts", [])
    data.setdefault("development_constitution", {})
    return data


def save_knowledge(knowledge: dict[str, Any], path: str | Path = KNOWLEDGE_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    save_json_atomic(p, knowledge)


def reflect_after_release(task: dict[str, Any]) -> dict[str, Any]:
    mission = task.get("mission", {})
    review = mission.get("final_review", {})
    logs = [log for log in load_agent_logs() if log.get("task_id") == task.get("task_id")]
    created_at = str(task.get("created_at") or "")
    updated_at = str(task.get("updated_at") or "")
    queue = mission.get("agent_queue", [])
    return {
        "reflection_id": f"rf-{uuid4().hex[:10]}",
        "task_id": task.get("task_id", ""),
        "pytest": review.get("checks", {}).get("pytest", False),
        "review": review,
        "agent_log_count": len(logs),
        "implementation_time": {"started_at": created_at, "finished_at": updated_at},
        "token_usage": task.get("result", {}).get("token_usage", "未計測"),
        "done_agents": sum(1 for item in queue if item.get("status") == "done"),
        "total_agents": len(queue),
        "created_at": _now(),
    }


def optimize_from_reflection(reflection: dict[str, Any]) -> dict[str, Any]:
    pytest_ok = bool(reflection.get("pytest"))
    all_agents_done = reflection.get("done_agents") == reflection.get("total_agents")
    return {
        "optimization_id": f"op-{uuid4().hex[:10]}",
        "reflection_id": reflection.get("reflection_id", ""),
        "prompt_improvement": "対象ファイル、禁止事項、確認コマンドを先に固定する",
        "code_improvement": "変更範囲を小さくし、保存処理は既存ユーティリティへ寄せる",
        "ui_improvement": "初心者が押すボタンを上段に集め、詳細操作は折りたたむ",
        "speed_improvement": "現状確認、差分確認、テストをAgentごとに分けて並列判断する",
        "token_reduction": "ログとKnowledge Baseから似たタスクの制約を再利用する",
        "quality": "success" if pytest_ok and all_agents_done else "improvement",
        "created_at": _now(),
    }


def save_release_learning(task: dict[str, Any], reflection: dict[str, Any], optimization: dict[str, Any]) -> dict[str, Any]:
    knowledge = load_knowledge()
    example = {
        "id": f"kb-{uuid4().hex[:10]}",
        "task_id": task.get("task_id", ""),
        "instruction": task.get("instruction", ""),
        "plan": task.get("plan", ""),
        "risk_level": task.get("risk_level", ""),
        "reflection": reflection,
        "optimization": optimization,
        "created_at": _now(),
    }
    if optimization.get("quality") == "success":
        knowledge["success_examples"].insert(0, example)
    else:
        knowledge["improvement_examples"].insert(0, example)
    if task.get("risk_level") == "high":
        knowledge["failure_examples"].insert(0, example)
    save_knowledge(knowledge)
    return example


def memory_context(instruction: str, plan: str) -> dict[str, Any]:
    knowledge = load_knowledge()
    text = instruction.lower()
    matched = []
    for group in ("success_examples", "failure_examples", "improvement_examples"):
        for item in knowledge.get(group, [])[:10]:
            source = f"{item.get('instruction', '')} {item.get('plan', '')}".lower()
            if plan.lower() in source or any(word and word in source for word in text.split()[:6]):
                matched.append({"type": group, "item": item})
    ranked_research = sorted(
        knowledge.get("research_results", [])[:50],
        key=lambda item: item.get("research_score", 0),
        reverse=True,
    )
    for item in ranked_research[:20]:
        source = f"{item.get('category', '')} {' '.join(item.get('tags', []))} {item.get('update_summary', '')}".lower()
        if any(word and word in source for word in text.split()[:8]):
            matched.append({"type": "research_results", "item": item})
    return {
        "matched_count": len(matched),
        "matches": matched[:3],
        "recommendation": "類似Knowledgeを参照してからMission Plannerへ渡す" if matched else "新規パターンとして小さく開始する",
    }


def continuous_builder_candidate(task: dict[str, Any], optimization: dict[str, Any]) -> dict[str, Any]:
    return {
        "instruction": (
            "前回Releaseの改善案を反映する。"
            f" Prompt改善: {optimization.get('prompt_improvement')}. "
            f"Token削減: {optimization.get('token_reduction')}."
        ),
        "plan": task.get("plan", "Free Plan"),
        "target_files": task.get("target_files", []),
        "source_task_id": task.get("task_id", ""),
    }
