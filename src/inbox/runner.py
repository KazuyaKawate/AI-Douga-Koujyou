from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from .models import InboxEntry, OutboxEntry
from .queue import TaskQueue

if TYPE_CHECKING:
    from src.ai.memory import BaseMemoryProvider
    from src.ai.response import AIResponse
    from src.ai.router import AIRouter
    from src.ai.snapshot import SnapshotBuilder


class TaskRunner:
    """
    TaskQueue からエントリを取り出し、AIRouter で処理する。

    Source に依存しない設計。Source 固有の status 更新は InboxPoller が担う。
    呼び出し元がフローを制御する:

        result = runner.run_once()
        if result:
            entry, resp = result
            poller.mark_done(entry.id) if resp.ok else poller.mark_error(...)
    """

    def __init__(
        self,
        router: "AIRouter",
        queue: TaskQueue,
        memory: "BaseMemoryProvider | None" = None,
        snapshot_builder: "SnapshotBuilder | None" = None,
        allow_write: bool = False,
    ) -> None:
        self._router   = router
        self._queue    = queue
        self._memory   = memory
        self._snapshot = snapshot_builder
        self._allow_write = allow_write

    # ---- Public API --------------------------------------------------

    def run_once(self) -> tuple[InboxEntry, "AIResponse"] | None:
        """
        Queue から 1件取り出して AIRouter で処理する。

        完了後（成功・失敗とも）queue.complete() を呼ぶ。
        Queue が空なら None を返す。
        Source の status 更新は呼び出し元（InboxPoller 経由）で行う。
        """
        entry = self._queue.get()
        if entry is None:
            return None

        try:
            task = self._entry_to_task(entry)
            resp = self._router.route(task)

            self._write_outbox(entry, resp)
            self._update_memory(entry, resp)
            self._save_snapshot()

            return entry, resp
        finally:
            self._queue.complete()  # 成功・失敗どちらでも完了マーク

    # ---- Private -----------------------------------------------------

    def _entry_to_task(self, entry: InboxEntry) -> "AITask":  # noqa: F821
        from src.ai.task import AITask, TaskType
        try:
            task_type = TaskType(entry.task_type)
        except ValueError:
            task_type = TaskType.DEFAULT
        return AITask(task_type=task_type, prompt=entry.prompt)

    def _write_outbox(self, entry: InboxEntry, resp: "AIResponse") -> None:
        """Outbox エントリを構築する。allow_write=True 時のみ Source に書き込む（将来実装）。"""
        meta = resp.metadata or {}
        outbox = OutboxEntry(
            inbox_id=entry.id,
            completed_at=datetime.now(),
            provider=resp.provider,
            model=resp.model,
            response=resp.content,
            input_tokens=meta.get("input_tokens"),
            output_tokens=meta.get("output_tokens"),
            cost_usd=meta.get("cost_usd"),
            error=resp.error,
        )
        if not self._allow_write:
            print(
                f"[dry-run] outbox: inbox_id={outbox.inbox_id}"
                f" provider={outbox.provider} ok={resp.ok}"
            )

    def _update_memory(self, entry: InboxEntry, resp: "AIResponse") -> None:
        """処理結果を Memory に記録する。memory が None なら何もしない。"""
        if self._memory is None:
            return
        try:
            from src.ai.memory import MemoryKey, MemoryScope, TTL
            self._memory.set(
                MemoryKey.CURRENT_TASK.value,
                entry.prompt[:200],
                MemoryScope.SESSION,
                TTL.SESSION,
            )
            self._memory.set(
                MemoryKey.PENDING_TASK.value,
                str(self._queue.size()),
                MemoryScope.GLOBAL,
                TTL.PERMANENT,
            )
        except Exception as exc:
            print(f"[warn] Memory 更新失敗: {exc}")

    def _save_snapshot(self) -> None:
        """Snapshot を保存する。snapshot_builder が None なら何もしない。"""
        if self._snapshot is None:
            return
        try:
            self._snapshot.save()
        except Exception as exc:
            print(f"[warn] Snapshot 保存失敗: {exc}")
