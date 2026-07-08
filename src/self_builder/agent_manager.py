from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic
from src.core.development_constitution import (
    development_review,
    ensure_development_constitution,
    evaluate_constitution_compliance,
)
from src.self_builder.risk_checker import assess_risk


AGENT_LOG_PATH = PROJECT_ROOT / "config" / "self_builder_agent_logs.json"

AGENTS = [
    "Mission Planner",
    "UI Agent",
    "Backend Agent",
    "Database Agent",
    "Test Agent",
    "Review Agent",
    "Release Agent",
    "Documentation Agent",
    "Reflection Agent",
    "Optimization Agent",
    "Knowledge Agent",
    "Memory Agent",
]

STATUS_FLOW = ["working", "waiting", "reviewing", "testing", "done"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _agent_task(agent: str, instruction: str, plan: str, target_files: list[str]) -> dict[str, Any]:
    action_map = {
        "Mission Planner": "ユーザー指示を解析し、各Agentへ作業を分配",
        "UI Agent": "画面、導線、初心者向け表示を確認",
        "Backend Agent": "処理分割、保存、状態管理を確認",
        "Database Agent": "JSON保存形式と履歴データを確認",
        "Test Agent": "確認コマンドとテスト観点を整理",
        "Review Agent": "差分、危険箇所、未完了を確認",
        "Release Agent": "承認後のみRelease候補へ送る準備",
        "Documentation Agent": "報告内容と操作説明を整理",
        "Reflection Agent": "Release後のpytest、Review、Agentログ、時間、Token使用量を解析",
        "Optimization Agent": "Prompt、コード、UI、速度、Token削減の改善案を生成",
        "Knowledge Agent": "成功例、失敗例、改善例をKnowledge Baseへ保存",
        "Memory Agent": "類似Knowledgeを参照してMission Plannerへ渡す",
    }
    return {
        "agent_id": f"ag-{uuid4().hex[:8]}",
        "agent": agent,
        "task": action_map[agent],
        "instruction": instruction,
        "plan": plan,
        "status": "working" if agent == "Mission Planner" else "waiting",
        "target_files": target_files,
        "constitution_reference": "Development Constitution v1.0",
        "created_at": _now(),
        "updated_at": _now(),
        "result": "",
    }


def mission_plan(instruction: str, plan: str, target_files: list[str] | None = None) -> dict[str, Any]:
    targets = target_files or []
    constitution = ensure_development_constitution()
    risk = assess_risk(instruction, targets)
    from src.self_builder.knowledge_manager import memory_context

    memory = memory_context(instruction, plan)
    dev_review = development_review(
        {
            "instruction": instruction,
            "plan": plan,
            "target_files": targets,
            "risk_level": risk["risk_level"],
        },
        context={"knowledge_duplication": memory.get("matched_count", 0)},
    )
    queue = [_agent_task(agent, instruction, plan, targets) for agent in AGENTS]
    for item in queue[:3]:
        item["status"] = "working"
    return {
        "mission_id": f"ms-{uuid4().hex[:10]}",
        "planner": "Mission Planner",
        "instruction": instruction,
        "plan": plan,
        "risk_level": risk["risk_level"],
        "risk_reasons": risk["reasons"],
        "memory_context": memory,
        "constitution": {
            "version": constitution.get("version", "1.0"),
            "priority_order": constitution.get("priority_order", []),
        },
        "development_review": dev_review,
        "agent_queue": queue,
        "status": "working",
        "created_at": _now(),
        "updated_at": _now(),
        "release_approved": False,
    }


def load_agent_logs(path: str | Path = AGENT_LOG_PATH) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def save_agent_logs(logs: list[dict[str, Any]], path: str | Path = AGENT_LOG_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    save_json_atomic(p, logs)


def append_agent_log(agent: str, action: str, task_id: str = "", changed: str = "") -> dict[str, Any]:
    log = {
        "log_id": f"log-{uuid4().hex[:10]}",
        "task_id": task_id,
        "agent": agent,
        "action": action,
        "changed": changed,
        "created_at": _now(),
    }
    logs = load_agent_logs()
    logs.insert(0, log)
    save_agent_logs(logs)
    return log


def advance_agent_queue(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    advanced = []
    for item in queue:
        current = str(item.get("status", "waiting"))
        if current in STATUS_FLOW:
            index = STATUS_FLOW.index(current)
            item["status"] = STATUS_FLOW[min(index + 1, len(STATUS_FLOW) - 1)]
            item["updated_at"] = _now()
        advanced.append(item)
    return advanced


def final_review(mission: dict[str, Any]) -> dict[str, Any]:
    queue = mission.get("agent_queue", [])
    done_count = sum(1 for item in queue if item.get("status") == "done")
    risk = mission.get("risk_level", "low")
    checks = {
        "差分確認": bool(queue) and done_count == len(queue),
        "pytest": bool(queue) and done_count == len(queue),
        "危険チェック": risk != "high",
    }
    compliance = evaluate_constitution_compliance(mission)
    checks["Constitution準拠"] = compliance["score"] >= 80
    missing = [name for name, ok in checks.items() if not ok]
    return {
        "status": "approved" if not missing else "needs_attention",
        "checks": checks,
        "missing": missing,
        "constitution_compliance": compliance,
        "reviewed_at": _now(),
    }


def approve_for_release(mission: dict[str, Any]) -> dict[str, Any]:
    review = final_review(mission)
    mission["final_review"] = review
    mission["release_approved"] = review["status"] == "approved"
    mission["updated_at"] = _now()
    return mission
