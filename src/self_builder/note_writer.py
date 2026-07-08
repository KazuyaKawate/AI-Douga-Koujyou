from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT


NOTE_DIR = PROJECT_ROOT / "config" / "self_builder_notes"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _compact(text: str, fallback: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    return cleaned or fallback


def _slug(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z_-]+", "-", text.strip().lower()).strip("-")
    return slug[:48] or "note"


def generate_note_title(task: dict[str, Any]) -> str:
    instruction = _compact(task.get("instruction", ""), "AIOS Self Builder実行ログ")
    if len(instruction) > 42:
        instruction = f"{instruction[:42].rstrip()}..."
    return f"AIOS開発ログ: {instruction}"


def generate_note_body(task: dict[str, Any]) -> str:
    mission = task.get("mission", {}) if isinstance(task.get("mission"), dict) else {}
    execution = task.get("execution", {}) if isinstance(task.get("execution"), dict) else {}
    worktree = task.get("worktree", {}) if isinstance(task.get("worktree"), dict) else {}
    agents = execution.get("queue", []) if isinstance(execution.get("queue"), list) else []
    agent_lines = [f"- {agent.get('agent', agent.get('name', 'Agent'))}: {agent.get('status', 'queued')}" for agent in agents]

    return "\n".join(
        [
            "## 今日の目的",
            _compact(task.get("instruction", ""), "AIOSの改善を進める。"),
            "",
            "## 実行計画",
            _compact(mission.get("summary", ""), "Mission Plannerが実行手順を整理しました。"),
            "",
            "## Execution Team",
            *(agent_lines or ["- Execution Team: queued"]),
            "",
            "## WorkTree",
            f"- Branch: {_compact(worktree.get('branch', ''), '未作成')}",
            f"- Merge: {_compact(worktree.get('merge_status', ''), 'pending')}",
            "",
            "## 次の確認",
            "- pytest該当テストのみ実行",
            "- 差分だけ報告",
        ]
    )


def save_note_markdown(
    task: dict[str, Any],
    *,
    title: str | None = None,
    body: str | None = None,
    note_dir: str | Path = NOTE_DIR,
) -> dict[str, Any]:
    note_title = title or generate_note_title(task)
    note_body = body or generate_note_body(task)
    task_id = _compact(task.get("task_id", ""), "self-builder")
    filename = f"{task_id}-{_slug(note_title)}.md"
    path = Path(note_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {note_title}\n\n{note_body}\n", encoding="utf-8")
    return {
        "title": note_title,
        "body": note_body,
        "markdown_path": str(path),
        "saved_at": _now(),
    }
