from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic
from src.self_builder.agent_manager import append_agent_log, mission_plan
from src.self_builder.execution_manager import build_execution_queue
from src.self_builder.note_writer import save_note_markdown
from src.self_builder.prompt_builder import build_codex_prompt
from src.self_builder.risk_checker import assess_risk
from src.self_builder.worktree_manager import plan_worktree


TASKS_PATH = PROJECT_ROOT / "config" / "self_builder_tasks.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_tasks(path: str | Path = TASKS_PATH) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def save_tasks(tasks: list[dict[str, Any]], path: str | Path = TASKS_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    save_json_atomic(p, tasks)


def create_task(
    instruction: str,
    plan: str,
    *,
    target_files: list[str] | None = None,
    path: str | Path = TASKS_PATH,
) -> dict[str, Any]:
    targets = target_files or []
    risk = assess_risk(instruction, targets)
    mission = mission_plan(instruction, plan, targets)
    now = _now()
    base_task = {
        "task_id": f"sb-{uuid4().hex[:10]}",
        "instruction": instruction.strip(),
        "plan": plan,
        "target_files": targets,
    }
    task = {
        "task_id": base_task["task_id"],
        "instruction": instruction.strip(),
        "plan": plan,
        "status": "queued",
        "risk_level": risk["risk_level"],
        "target_files": targets,
        "mission": mission,
        "execution": build_execution_queue(base_task),
        "worktree": plan_worktree(base_task),
        "created_at": now,
        "updated_at": now,
        "result": {
            "risk_reasons": risk["reasons"],
            "codex_prompt": build_codex_prompt(instruction, plan, risk),
        },
    }
    task["result"]["note"] = save_note_markdown(task)
    tasks = load_tasks(path)
    tasks.insert(0, task)
    save_tasks(tasks, path)
    append_agent_log("Mission Planner", "タスクを解析しAgent Queueを生成", task["task_id"], ", ".join(targets))
    return task


def update_task_status(task_id: str, status: str, result: dict[str, Any] | None = None) -> dict[str, Any] | None:
    tasks = load_tasks()
    updated = None
    for task in tasks:
        if task.get("task_id") == task_id:
            task["status"] = status
            task["updated_at"] = _now()
            if result:
                task["result"] = {**task.get("result", {}), **result}
            updated = task
            break
    if updated:
        save_tasks(tasks)
    return updated
