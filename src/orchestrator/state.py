from __future__ import annotations
import threading
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from .models import JobStatus, WorkflowJob

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStatus


class OrchestratorState:
    """
    Orchestrator のランタイム状態をスレッドセーフに管理する。

    WorkflowJob の CRUD と、実行中ワークフローへの参照 (_active_wf) を保持する。
    全操作は _lock で保護される。
    """

    def __init__(self) -> None:
        self._jobs:      dict[str, WorkflowJob]       = {}
        self._active_wf: dict[str, "WorkflowStatus"]  = {}   # job_id → WorkflowStatus
        self._lock       = threading.Lock()

    # ---- Job CRUD ------------------------------------------------

    def add_job(self, job: WorkflowJob) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def update_job(self, job: WorkflowJob) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def get_job(self, job_id: str) -> Optional[WorkflowJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, status_filter: JobStatus | None = None) -> list[WorkflowJob]:
        with self._lock:
            jobs = list(self._jobs.values())
        if status_filter is not None:
            jobs = [j for j in jobs if j.status == status_filter]
        return jobs

    def get_running_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING)

    def get_next_pending_jobs(self, limit: int = 1) -> list[WorkflowJob]:
        """
        実行可能な PENDING ジョブを優先度順（高→低、同一優先度は作成順）で返す。

        - retry_after が設定されている場合は現在時刻と比較する。
        - depends_on の全ジョブが COMPLETED かチェックする。
        """
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            eligible = [
                j for j in self._jobs.values()
                if j.status == JobStatus.PENDING
                and (j.retry_after is None or j.retry_after <= now)
                and self._all_deps_completed_unlocked(j)
            ]
        eligible.sort(key=lambda j: (-j.priority, j.created_at))
        return eligible[:limit]

    def _all_deps_completed_unlocked(self, job: WorkflowJob) -> bool:
        """ロック保持中に呼ぶ。依存ジョブが全て COMPLETED か確認する。"""
        for dep_id in job.depends_on:
            dep = self._jobs.get(dep_id)
            if not dep or dep.status != JobStatus.COMPLETED:
                return False
        return True

    # ---- Active WorkflowStatus 参照 ----------------------------

    def set_active_wf_status(self, job_id: str, wf_status: "WorkflowStatus") -> None:
        """実行中ジョブの WorkflowStatus オブジェクト参照を保存する。"""
        with self._lock:
            self._active_wf[job_id] = wf_status

    def get_active_wf_status(self, job_id: str) -> Optional["WorkflowStatus"]:
        """実行中ジョブの WorkflowStatus オブジェクト参照を返す。"""
        with self._lock:
            return self._active_wf.get(job_id)

    def remove_active_wf_status(self, job_id: str) -> None:
        """完了・失敗・キャンセル後に参照を解放する。"""
        with self._lock:
            self._active_wf.pop(job_id, None)
