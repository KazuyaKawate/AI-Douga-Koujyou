from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic


WORKTREE_HISTORY_PATH = PROJECT_ROOT / "config" / "self_builder_worktree_history.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def branch_name_for(task_id: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in task_id).strip("-")
    return f"codex/self-builder-{safe or uuid4().hex[:8]}"


def plan_worktree(task: dict[str, Any]) -> dict[str, Any]:
    task_id = str(task.get("task_id", "task"))
    return {
        "worktree_id": f"wt-{uuid4().hex[:10]}",
        "task_id": task_id,
        "branch": branch_name_for(task_id),
        "merge_status": "not_started",
        "release_status": "not_released",
        "created_at": _now(),
        "history": [
            {
                "event": "branch_plan_created",
                "branch": branch_name_for(task_id),
                "created_at": _now(),
            }
        ],
    }


def record_worktree_history(record: dict[str, Any]) -> None:
    WORKTREE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if WORKTREE_HISTORY_PATH.exists():
        try:
            import json

            raw = json.loads(WORKTREE_HISTORY_PATH.read_text(encoding="utf-8"))
            history = raw if isinstance(raw, list) else []
        except Exception:
            history = []
    history.insert(0, record)
    save_json_atomic(WORKTREE_HISTORY_PATH, history)


def mark_merge_planned(worktree: dict[str, Any]) -> dict[str, Any]:
    worktree["merge_status"] = "planned"
    worktree["history"].insert(0, {"event": "merge_planned", "created_at": _now()})
    record_worktree_history(worktree)
    return worktree


def mark_release_recorded(worktree: dict[str, Any]) -> dict[str, Any]:
    worktree["release_status"] = "recorded"
    worktree["history"].insert(0, {"event": "release_recorded", "created_at": _now()})
    record_worktree_history(worktree)
    return worktree

