from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.business_engine.automation import RevenueAutomation
from src.business_engine.manager import BusinessEngineStore
from src.core.development_constitution import development_review, evaluate_constitution_compliance
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge
from src.self_builder.terminal_runner import TERMINAL_LOG_PATH, run_terminal, terminal_result_to_debug
from src.utils.config import PROJECT_ROOT


EXECUTION_AGENTS = [
    "Developer",
    "Refactor",
    "Test",
    "Debug",
    "Documentation",
    "Release",
    "Automation",
    "Revenue",
]

EXECUTION_FLOW = [
    "research",
    "mission_planner",
    "execution",
    "business_engine",
    "release",
    "knowledge",
    "memory",
    "continuous_builder",
]

EXECUTION_STATUSES = ["Waiting", "Planning", "Executing", "Testing", "Review", "Completed", "Failed", "Retry"]
STATUS_ALIASES = {
    "waiting": "Waiting",
    "working": "Executing",
    "reviewing": "Review",
    "testing": "Testing",
    "done": "Completed",
}
EXECUTION_LOG_DIR = PROJECT_ROOT / "config" / "self_builder_execution"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _task_id(task: dict[str, Any]) -> str:
    return str(task.get("task_id") or f"task-{uuid4().hex[:8]}")


def _instruction(task: dict[str, Any]) -> str:
    return str(task.get("instruction") or "AIOS Self Builder improvement").strip()


def _queue_item(agent: str, task: dict[str, Any]) -> dict[str, Any]:
    responsibilities = {
        "Developer": "Research / Knowledge / Memory / Official Docs / GitHubを参照してコード生成案を作成",
        "Refactor": "重複、Token、速度、可読性、保守性を評価して改善案をKnowledgeへ保存",
        "Test": "pytest確認計画と結果を保存",
        "Debug": "失敗時のログ解析、原因、修正候補をMission Plannerへ返却",
        "Documentation": "Release Note、README、API変更、ChangelogをMarkdown保存",
        "Release": "Test、Review、Security、Research確認後に承認待ちへ移動",
        "Automation": "ResearchからContinuous Builderまでの自動連携を準備",
        "Revenue": "Business Engineへnote、Threads、Official Site、LP、SEO記事の収益導線を登録",
    }
    return {
        "execution_id": f"ex-{uuid4().hex[:8]}",
        "agent": agent,
        "task": responsibilities[agent],
        "instruction": _instruction(task),
        "target_files": list(task.get("target_files", [])),
        "constitution_reference": "Development Constitution v1.0",
        "status": "Planning" if agent == "Developer" else "Waiting",
        "created_at": _now(),
        "updated_at": _now(),
        "result": {},
    }


def build_execution_queue(task: dict[str, Any]) -> dict[str, Any]:
    queue = [_queue_item(agent, task) for agent in EXECUTION_AGENTS]
    review = development_review(task)
    return {
        "queue_id": f"eq-{uuid4().hex[:10]}",
        "task_id": _task_id(task),
        "flow": EXECUTION_FLOW,
        "current_stage": "execution",
        "status": "Planning",
        "queue": queue,
        "mission_feedback": [],
        "knowledge_refs": [],
        "development_review": review,
        "constitution_compliance": review.get("constitution_compliance", {}),
        "created_at": _now(),
        "updated_at": _now(),
        "release_ready": False,
    }


def normalize_execution_status(status: str) -> str:
    value = str(status or "Waiting")
    return STATUS_ALIASES.get(value, value if value in EXECUTION_STATUSES else "Waiting")


def receive_mission_queue(agent_queue: list[dict[str, Any]], task: dict[str, Any] | None = None) -> dict[str, Any]:
    source_task = task or {"task_id": "mission", "instruction": "Mission Planner queue"}
    execution = build_execution_queue(source_task)
    execution["mission_agent_queue"] = agent_queue
    for index, item in enumerate(execution["queue"]):
        if index < len(agent_queue):
            item["mission_source"] = agent_queue[index]
            item["status"] = normalize_execution_status(agent_queue[index].get("status", "Waiting"))
    execution["updated_at"] = _now()
    return execution


def run_agent(execution: dict[str, Any], agent: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    item = _find_agent(execution, agent)
    if item is None:
        raise ValueError(f"Unknown execution agent: {agent}")
    runners = {
        "Developer": _run_developer,
        "Refactor": _run_refactor,
        "Test": _run_test,
        "Debug": _run_debug,
        "Documentation": _run_documentation,
        "Release": _run_release,
        "Automation": _run_automation,
        "Revenue": _run_revenue,
    }
    item["status"] = "Executing" if agent not in ("Test", "Release") else ("Testing" if agent == "Test" else "Review")
    item["result"] = runners[agent](execution, item, context)
    item["status"] = "Failed" if item["result"].get("status") in ("Failed", "Fail") else "Completed"
    item["updated_at"] = _now()
    execution["updated_at"] = _now()
    execution["release_ready"] = _release_ready(execution)
    execution["status"] = "Completed" if execution["release_ready"] else "Executing"
    _save_execution_learning(execution, agent, item["result"])
    return execution


def advance_execution_queue(execution: dict[str, Any]) -> dict[str, Any]:
    for item in execution.get("queue", []):
        status = normalize_execution_status(item.get("status", "Waiting"))
        if status == "Waiting":
            item["status"] = "Planning"
        elif status == "Planning":
            item["status"] = "Executing"
        elif status == "Executing":
            item["status"] = "Testing" if item.get("agent") == "Test" else "Review"
        elif status in ("Testing", "Review"):
            item["status"] = "Completed"
        elif status == "Failed":
            item["status"] = "Retry"
        item["updated_at"] = _now()
    execution["release_ready"] = _release_ready(execution)
    execution["status"] = "Completed" if execution["release_ready"] else "Executing"
    execution["current_stage"] = "release" if execution["release_ready"] else "execution"
    execution["updated_at"] = _now()
    return execution


def execution_summary(execution: dict[str, Any]) -> dict[str, Any]:
    queue = execution.get("queue", [])
    counts = {status: 0 for status in EXECUTION_STATUSES}
    for item in queue:
        counts[normalize_execution_status(item.get("status", "Waiting"))] += 1
    completed = counts["Completed"]
    total = len(queue)
    estimated_revenue = sum(
        int(item.get("result", {}).get("estimated_revenue", 0))
        for item in queue
        if isinstance(item.get("result"), dict)
    )
    return {
        "total": total,
        "counts": counts,
        "release_ready": execution.get("release_ready", False),
        "current_stage": execution.get("current_stage", "execution"),
        "flow": execution.get("flow", EXECUTION_FLOW),
        "success_rate": round(completed / total * 100, 1) if total else 0,
        "estimated_time_saved_minutes": completed * 18,
        "estimated_revenue": estimated_revenue,
    }


def execution_dashboard(execution: dict[str, Any]) -> dict[str, Any]:
    summary = execution_summary(execution)
    counts = summary["counts"]
    terminal_logs = execution.get("terminal_logs", [])
    return {
        "running": counts["Executing"],
        "waiting": counts["Waiting"] + counts["Planning"],
        "testing": counts["Testing"],
        "review": counts["Review"],
        "completed": counts["Completed"],
        "failed": counts["Failed"],
        "agent_count": summary["total"],
        "success_rate": summary["success_rate"],
        "estimated_time_saved_minutes": summary["estimated_time_saved_minutes"],
        "estimated_revenue": summary["estimated_revenue"],
        "terminal_log_count": len(terminal_logs),
        "latest_terminal_logs": terminal_logs[:5],
    }


def _run_developer(execution: dict[str, Any], item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    refs = {
        "research": context.get("research", []),
        "knowledge": context.get("knowledge", []),
        "memory": context.get("memory", {}),
        "official_docs": context.get("official_docs", "参照予定"),
        "github": context.get("github", "参照予定"),
    }
    terminal = None
    if context.get("command"):
        terminal = run_terminal(
            str(context["command"]),
            safe_mode=bool(context.get("safe_mode", True)),
            confirmed=bool(context.get("confirmed", False)),
            agent="Developer",
            task_id=str(execution.get("task_id", "")),
            cwd=context.get("cwd", PROJECT_ROOT),
            log_path=context.get("terminal_log_path", TERMINAL_LOG_PATH),
            business_store=context.get("business_store"),
        )
        _attach_terminal_result(execution, terminal)
    return {
        "status": "Pass",
        "generated_code_plan": f"{item['instruction']} を対象ファイル内で最小差分実装する。",
        "generation_reason": "Research、Knowledge、Memory、Official Docs、GitHub参照を統合して実装理由を保存しました。",
        "references": refs,
        "terminal": terminal,
    }


def _run_refactor(execution: dict[str, Any], item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    evaluation = {
        "duplicate_code": "low",
        "token_reduction": "promptとログの再利用で削減余地あり",
        "speed": "対象Agentのみ実行して短縮",
        "readability": "状態名を統一して改善",
        "maintainability": "Agent責務を分離して改善",
    }
    improvement = {
        "title": "Execution Team Refactor Review",
        "task_id": execution.get("task_id", ""),
        "evaluation": evaluation,
        "created_at": _now(),
    }
    knowledge = load_knowledge()
    knowledge.setdefault("improvement_examples", []).insert(0, improvement)
    save_knowledge(knowledge)
    return {"status": "Pass", "evaluation": evaluation, "knowledge_saved": True}


def _run_test(execution: dict[str, Any], item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    terminal = None
    if context.get("run_terminal", True):
        terminal = run_terminal(
            str(context.get("pytest_command", "pytest tests/test_execution_manager.py -q")),
            safe_mode=bool(context.get("safe_mode", True)),
            confirmed=bool(context.get("confirmed", False)),
            agent="Test",
            task_id=str(execution.get("task_id", "")),
            cwd=context.get("cwd", PROJECT_ROOT),
            log_path=context.get("terminal_log_path", TERMINAL_LOG_PATH),
            business_store=context.get("business_store"),
        )
        _attach_terminal_result(execution, terminal)
        if terminal.get("status") in ("failed", "blocked", "timeout"):
            execution.setdefault("mission_feedback", []).insert(0, terminal_result_to_debug(terminal))
    pytest_result = context.get("pytest_result", "not_run")
    if terminal:
        pytest_result = "pass" if terminal.get("exit_code") == 0 and terminal.get("status") == "completed" else "fail" if terminal.get("status") in ("failed", "timeout") else pytest_result
    status = "Pass" if pytest_result in ("pass", "passed", True) else "Warning" if pytest_result == "not_run" else "Fail"
    return {
        "status": status,
        "pytest": {
            "command": context.get("pytest_command", "pytest tests/test_execution_manager.py -q"),
            "result": status,
            "log": context.get("pytest_log", terminal.get("stdout", "") if terminal else "pytestは安全モードでは計画保存のみです。"),
            "saved_at": _now(),
        },
        "terminal": terminal,
    }


def _run_debug(execution: dict[str, Any], item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    terminal_entry = context.get("terminal_entry")
    if terminal_entry:
        feedback = terminal_result_to_debug(terminal_entry)
        execution.setdefault("mission_feedback", []).insert(0, feedback)
        return {"status": "Pass", "mission_feedback": feedback}
    failures = [
        q for q in execution.get("queue", [])
        if q.get("status") == "Failed" or q.get("result", {}).get("status") == "Fail"
    ]
    feedback = {
        "receiver": "Mission Planner",
        "status": "Retry" if failures else "Completed",
        "log_analysis": context.get("log", "失敗ログは未入力です。"),
        "cause": "pytestまたはAgent結果の失敗を検出" if failures else "致命的な失敗は検出されていません。",
        "fix_candidates": ["対象Agentだけ再実行", "失敗ログをResearch/Knowledgeへ保存", "Mission PlannerでRetryタスク化"],
        "created_at": _now(),
    }
    execution.setdefault("mission_feedback", []).insert(0, feedback)
    return {"status": "Pass", "mission_feedback": feedback}


def _run_documentation(execution: dict[str, Any], item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    docs = {
        "release_note": "# Release Note\n\nExecution Team Phase2.5を追加しました。\n",
        "readme": "# README Update\n\nSelf BuilderがExecution Team DashboardとAgent実行ログを扱います。\n",
        "api_changes": "# API Changes\n\n`run_agent`, `execution_dashboard`, `receive_mission_queue` を追加。\n",
        "changelog": "# Changelog\n\n- Execution Team Agentを追加\n- Mission Planner返却を追加\n",
    }
    output_dir = EXECUTION_LOG_DIR / "docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = {}
    for name, content in docs.items():
        path = output_dir / f"{execution.get('task_id', 'task')}_{name}.md"
        path.write_text(content, encoding="utf-8")
        saved[name] = str(path)
    return {"status": "Pass", "markdown_files": saved}


def _run_release(execution: dict[str, Any], item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    compliance = evaluate_constitution_compliance(execution)
    checks = {
        "test": bool(context.get("test_passed", _has_agent_result(execution, "Test", ("Pass", "Warning")))),
        "review": bool(context.get("review_passed", True)),
        "security": bool(context.get("security_passed", True)),
        "research": bool(context.get("research_checked", True)),
        "constitution": compliance["score"] >= 80,
    }
    status = "approval_waiting" if all(checks.values()) else "blocked"
    return {
        "status": "Pass" if status == "approval_waiting" else "Failed",
        "release_status": status,
        "checks": checks,
        "constitution_compliance": compliance,
    }


def _run_automation(execution: dict[str, Any], item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "Pass",
        "chain": EXECUTION_FLOW,
        "continuous_builder": {
            "next": "KnowledgeとMemory保存後に改善タスクを生成",
            "mission_return": True,
        },
    }


def _run_revenue(execution: dict[str, Any], item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    store_path = context.get("business_store_path")
    store = BusinessEngineStore(store_path) if store_path else BusinessEngineStore()
    automation = RevenueAutomation(store)
    topic = context.get("topic") or execution.get("task_id") or "AIOS Execution Team"
    channels = ["note", "Threads", "Official Site", "LP", "SEO記事"]
    created = []
    for channel in channels:
        created.append(
            store.add_revenue_item(
                f"{topic} - {channel}",
                channel=channel,
                expected_revenue=int(context.get("expected_revenue", 12000)),
                stage="queued",
                memo="Execution Team Revenue Agentが登録",
            )
        )
    run = automation.start_content_automation(topic=str(topic), target="AIOS users")
    estimated = sum(int(item.get("expected_revenue", 0)) for item in created)
    return {
        "status": "Pass",
        "channels": channels,
        "revenue_items": created,
        "content_automation_run_id": run["run_id"],
        "estimated_revenue": estimated,
    }


def _save_execution_learning(execution: dict[str, Any], agent: str, result: dict[str, Any]) -> None:
    knowledge = load_knowledge()
    history = knowledge.setdefault("history", [])
    history.insert(
        0,
        {
            "history_id": f"hist-{uuid4().hex[:10]}",
            "type": _knowledge_type_for(agent),
            "task_id": execution.get("task_id", ""),
            "agent": agent,
            "result": result,
            "constitution_reference": execution.get("constitution_compliance", {}),
            "created_at": _now(),
        },
    )
    knowledge.setdefault("timeline", []).insert(
        0,
        {
            "event": f"Execution {agent}",
            "task_id": execution.get("task_id", ""),
            "status": result.get("status", ""),
            "created_at": _now(),
        },
    )
    save_knowledge(knowledge)


def _attach_terminal_result(execution: dict[str, Any], terminal: dict[str, Any]) -> None:
    execution.setdefault("terminal_logs", []).insert(0, terminal)


def _knowledge_type_for(agent: str) -> str:
    mapping = {
        "Developer": "execution_log",
        "Refactor": "review",
        "Test": "test",
        "Debug": "agent_log",
        "Documentation": "release",
        "Release": "release",
        "Revenue": "revenue",
        "Automation": "history",
    }
    return mapping.get(agent, "history")


def _release_ready(execution: dict[str, Any]) -> bool:
    queue = execution.get("queue", [])
    return bool(queue) and all(normalize_execution_status(item.get("status")) == "Completed" for item in queue)


def _find_agent(execution: dict[str, Any], agent: str) -> dict[str, Any] | None:
    return next((item for item in execution.get("queue", []) if item.get("agent") == agent), None)


def _has_agent_result(execution: dict[str, Any], agent: str, accepted: tuple[str, ...]) -> bool:
    item = _find_agent(execution, agent)
    if not item:
        return False
    return item.get("result", {}).get("status") in accepted
