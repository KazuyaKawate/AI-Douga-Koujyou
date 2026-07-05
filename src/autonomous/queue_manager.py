"""AutonomousQueue — 改善タスクをキューで管理する。

優先度順キュー。data/autonomous/queue.json に永続化。
SafeMode がこのキューからタスクを取り出して実行する。
"""
from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from src.utils.json_store import save_json_atomic

_QUEUE_FILE = Path("data/autonomous/queue.json")
_lock       = threading.Lock()


class TaskStatus:
    PENDING      = "pending"       # 実行待ち
    RUNNING      = "running"       # 実行中
    PATCH_READY  = "patch_ready"   # Patch 生成完了・承認待ち
    APPROVED     = "approved"      # 承認済み・Merge 待ち
    MERGED       = "merged"        # Merge 完了
    REJECTED     = "rejected"      # 却下
    FAILED       = "failed"        # 実行失敗
    CANCELLED    = "cancelled"     # キャンセル


@dataclass
class ImprovementTask:
    """キューの1タスク。"""
    task_id:        str
    title:          str
    task_type:      str            # ActionType.*
    target:         str            # workflow/agent/factory ID
    description:    str
    priority:       int            # 1〜10 (高いほど優先)
    status:         str            # TaskStatus.*
    workflow_to_run:str            # dev.fix_bug / dev.add_feature / etc.
    context:        dict           # workflow に渡す context
    created_at:     str
    started_at:     Optional[str]  = None
    completed_at:   Optional[str]  = None
    patch_path:     Optional[str]  = None  # 生成された .patch ファイルパス
    review_summary: str            = ""    # AI レビュー結果
    review_score:   Optional[float]= None  # AI レビュースコア (0〜10)
    approved_by:    Optional[str]  = None  # "human" or "ai_auto"
    rejected_reason:str            = ""
    notes:          str            = ""
    source:         str            = "manual"  # "planner" | "manual" | "trigger"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ImprovementTask":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def is_active(self) -> bool:
        return self.status in (TaskStatus.PENDING, TaskStatus.RUNNING)


class AutonomousQueue:
    """
    改善タスクの優先度順キュー。

    使い方:
        q = AutonomousQueue()
        t = q.enqueue("コードレビュー", "fix_workflow", "dev.code_review", context={...})
        q.set_status(t.task_id, TaskStatus.RUNNING)
        q.set_patch(t.task_id, patch_path="output/dev/diff_xxx.patch")
    """

    def __init__(self) -> None:
        self._tasks: dict[str, ImprovementTask] = {}
        self._load()

    # ── キュー操作 ─────────────────────────────────────────────────

    def enqueue(
        self,
        title:           str,
        task_type:       str,
        workflow_to_run: str,
        target:          str = "",
        description:     str = "",
        priority:        int = 5,
        context:         dict | None = None,
        source:          str = "manual",
    ) -> ImprovementTask:
        t = ImprovementTask(
            task_id        = str(uuid.uuid4())[:8],
            title          = title,
            task_type      = task_type,
            target         = target,
            description    = description,
            priority       = priority,
            status         = TaskStatus.PENDING,
            workflow_to_run= workflow_to_run,
            context        = context or {},
            created_at     = datetime.now().isoformat(timespec="seconds"),
            source         = source,
        )
        with _lock:
            self._tasks[t.task_id] = t
        self._save()
        return t

    def next_pending(self) -> Optional[ImprovementTask]:
        """優先度・作成日時順に次の PENDING タスクを返す（取り出しはしない）。"""
        pending = [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]
        if not pending:
            return None
        return sorted(pending, key=lambda t: (-t.priority, t.created_at))[0]

    def get(self, task_id: str) -> Optional[ImprovementTask]:
        return self._tasks.get(task_id)

    def list_all(self, status: Optional[str] = None) -> list[ImprovementTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: (-t.priority, t.created_at))

    def set_status(self, task_id: str, status: str) -> bool:
        t = self._tasks.get(task_id)
        if not t:
            return False
        t.status = status
        now = datetime.now().isoformat(timespec="seconds")
        if status == TaskStatus.RUNNING:
            t.started_at = now
        elif status in (TaskStatus.MERGED, TaskStatus.REJECTED, TaskStatus.FAILED):
            t.completed_at = now
        self._save()
        return True

    def set_patch(self, task_id: str, patch_path: str, review_summary: str = "", review_score: Optional[float] = None) -> bool:
        t = self._tasks.get(task_id)
        if not t:
            return False
        t.patch_path     = patch_path
        t.review_summary = review_summary
        t.review_score   = review_score
        t.status         = TaskStatus.PATCH_READY
        self._save()
        return True

    def approve(self, task_id: str, approved_by: str = "human") -> bool:
        t = self._tasks.get(task_id)
        if not t:
            return False
        t.approved_by = approved_by
        t.status      = TaskStatus.APPROVED
        self._save()
        return True

    def reject(self, task_id: str, reason: str = "") -> bool:
        t = self._tasks.get(task_id)
        if not t:
            return False
        t.status          = TaskStatus.REJECTED
        t.rejected_reason = reason
        t.completed_at    = datetime.now().isoformat(timespec="seconds")
        self._save()
        return True

    def merge(self, task_id: str) -> bool:
        """承認済みタスクを MERGED 状態にする（実ファイル変更は SafeMode が行う）。"""
        t = self._tasks.get(task_id)
        if not t or t.status != TaskStatus.APPROVED:
            return False
        t.status       = TaskStatus.MERGED
        t.completed_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return True

    def cancel(self, task_id: str) -> bool:
        t = self._tasks.get(task_id)
        if not t:
            return False
        t.status = TaskStatus.CANCELLED
        self._save()
        return True

    def update_notes(self, task_id: str, notes: str) -> bool:
        t = self._tasks.get(task_id)
        if not t:
            return False
        t.notes = notes
        self._save()
        return True

    def stats(self) -> dict:
        tasks = list(self._tasks.values())
        result = {s: 0 for s in [
            TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PATCH_READY,
            TaskStatus.APPROVED, TaskStatus.MERGED, TaskStatus.REJECTED,
            TaskStatus.FAILED, TaskStatus.CANCELLED,
        ]}
        for t in tasks:
            result[t.status] = result.get(t.status, 0) + 1
        result["total"] = len(tasks)
        return result

    # ── Persistence ────────────────────────────────────────────────

    def _save(self) -> None:
        _QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {tid: t.to_dict() for tid, t in self._tasks.items()}
        with _lock:
            save_json_atomic(_QUEUE_FILE, data)

    def _load(self) -> None:
        if not _QUEUE_FILE.exists():
            return
        try:
            data = json.loads(_QUEUE_FILE.read_text(encoding="utf-8"))
            self._tasks = {tid: ImprovementTask.from_dict(td) for tid, td in data.items()}
        except Exception:
            self._tasks = {}


# Singleton
_q_instance: Optional[AutonomousQueue] = None
_q_lock = threading.Lock()

def get_autonomous_queue() -> AutonomousQueue:
    global _q_instance
    if _q_instance is None:
        with _q_lock:
            if _q_instance is None:
                _q_instance = AutonomousQueue()
    return _q_instance

