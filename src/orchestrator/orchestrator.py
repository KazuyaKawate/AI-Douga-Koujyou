from __future__ import annotations
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from .events import Event, EventBus, EventType
from .models import JobStatus, OrchestratorConfig, OrchestratorStatus, WorkflowJob
from .registry import FactoryRegistry
from .state import OrchestratorState

from src.utils.json_store import save_json_atomic
if TYPE_CHECKING:
    from src.workflow.runner import WorkflowRunner
    from src.workflow.models import WorkflowStatus

_DEFAULT_STATUS_PATH = Path("data/orchestrator_status.json")


class FactoryOrchestrator:
    """
    複数 WorkflowJob を統括する Factory Orchestrator。

    WorkflowRunner / Inbox / Scheduler は変更せず、
    外部から run_async() / pause() / resume() / cancel() を呼ぶ構成。

    主要機能:
        submit()          ... WorkflowJob をキューに投入
        start()           ... バックグラウンドループで自律実行
        stop()            ... グレースフルシャットダウン
        run_job_now()     ... 同期・手動実行（テスト / Scheduler 連携）
        cancel_job()      ... ジョブキャンセル
        pause_job()       ... ジョブ一時停止
        resume_job()      ... ジョブ再開
        submit_from_inbox() ... Inbox エントリから Workflow 生成・投入
    """

    def __init__(
        self,
        workflow_runner: "WorkflowRunner",
        config: OrchestratorConfig,
        event_bus: Optional[EventBus] = None,
        registry: Optional[FactoryRegistry] = None,
        status_path: Path = _DEFAULT_STATUS_PATH,
        poll_sec: float = 1.0,
    ) -> None:
        self._runner      = workflow_runner
        self._config      = config
        self._event_bus   = event_bus or EventBus()
        self._registry    = registry or FactoryRegistry()
        self._state       = OrchestratorState()
        self._orch_status = OrchestratorStatus()
        self._status_path = status_path
        self._poll_sec    = poll_sec
        self._stop_event  = threading.Event()
        self._thread:     Optional[threading.Thread] = None

    # ---- Public: Job Management --------------------------------

    def submit(
        self,
        definition_name: str,
        priority:    int            = 5,
        context:     dict | None    = None,
        depends_on:  list[str] | None = None,
    ) -> str:
        """WorkflowJob をキューに投入し、job_id を返す。"""
        job = WorkflowJob(
            definition_name=definition_name,
            priority=priority,
            context=dict(context) if context else {},
            depends_on=list(depends_on) if depends_on else [],
            retry_max=self._config.retry_max,
            retry_delay_sec=self._config.retry_delay_sec,
        )
        self._state.add_job(job)
        return job.job_id

    def submit_from_inbox(
        self,
        entry: object,
        definition_name: str,
        priority: int = 5,
    ) -> str:
        """
        Inbox エントリから WorkflowJob を生成してキューに投入する。

        entry は id / prompt / task_type / source_name 属性を持つオブジェクトを想定する。
        """
        context = {
            "inbox_id":    getattr(entry, "id",          None),
            "prompt":      getattr(entry, "prompt",      ""),
            "task_type":   getattr(entry, "task_type",   ""),
            "source_name": getattr(entry, "source_name", ""),
        }
        return self.submit(
            definition_name=definition_name,
            priority=priority,
            context=context,
        )

    def cancel_job(self, job_id: str) -> bool:
        """ジョブをキャンセルする（PENDING / RUNNING / PAUSED が対象）。"""
        job = self._state.get_job(job_id)
        if not job or job.status not in (
            JobStatus.PENDING, JobStatus.RUNNING, JobStatus.PAUSED
        ):
            return False

        if job.status in (JobStatus.RUNNING, JobStatus.PAUSED) and job.workflow_id:
            self._runner.cancel(job.workflow_id)

        job.status   = JobStatus.CANCELLED
        job.ended_at = datetime.now().isoformat(timespec="seconds")
        self._state.update_job(job)
        self._state.remove_active_wf_status(job_id)
        self._event_bus.publish(Event(
            EventType.WORKFLOW_CANCELLED, {"job_id": job_id}
        ))
        return True

    def pause_job(self, job_id: str) -> bool:
        """実行中ジョブを一時停止する。"""
        job = self._state.get_job(job_id)
        if not job or job.status != JobStatus.RUNNING:
            return False

        if job.workflow_id:
            self._runner.pause(job.workflow_id)

        job.status = JobStatus.PAUSED
        self._state.update_job(job)
        self._event_bus.publish(Event(
            EventType.WORKFLOW_PAUSED, {"job_id": job_id}
        ))
        return True

    def resume_job(self, job_id: str) -> bool:
        """一時停止中ジョブを再開する。"""
        job = self._state.get_job(job_id)
        if not job or job.status != JobStatus.PAUSED:
            return False

        if job.workflow_id:
            self._runner.resume(job.workflow_id)

        job.status = JobStatus.RUNNING
        self._state.update_job(job)
        self._event_bus.publish(Event(
            EventType.WORKFLOW_RESUMED, {"job_id": job_id}
        ))
        return True

    def get_job(self, job_id: str) -> Optional[WorkflowJob]:
        return self._state.get_job(job_id)

    def list_jobs(
        self, status_filter: JobStatus | None = None
    ) -> list[WorkflowJob]:
        return self._state.list_jobs(status_filter)

    # ---- Public: Execution Control ----------------------------

    def start(self) -> None:
        """バックグラウンドループを起動する。二重起動は無視する。"""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._orch_status.running    = True
        self._orch_status.started_at = datetime.now().isoformat(timespec="seconds")
        self._flush_status()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="FactoryOrchestrator",
        )
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        """グレースフルシャットダウン。"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._orch_status.running = False
        self._flush_status()

    def is_running(self) -> bool:
        """バックグラウンドループが稼働中か返す。"""
        return bool(self._thread and self._thread.is_alive())

    def get_orchestrator_status(self) -> OrchestratorStatus:
        self._update_orch_status()
        return self._orch_status

    def run_job_now(
        self,
        definition_name: str,
        context: dict | None = None,
    ) -> WorkflowJob:
        """
        1ジョブを同期・手動実行する。リトライも同期で実行する。

        バックグラウンドループを使わず、呼び出しスレッドでブロックする。
        Scheduler 起動・テスト・手動操作向け。
        """
        definition = self._registry.get_workflow(definition_name)
        if definition is None:
            raise ValueError(
                f"Workflow が Registry に未登録: {definition_name!r}"
            )

        job = WorkflowJob(
            definition_name=definition_name,
            retry_max=self._config.retry_max,
            retry_delay_sec=self._config.retry_delay_sec,
            context=dict(context) if context else {},
        )
        self._state.add_job(job)

        while True:
            job.status        = JobStatus.RUNNING
            job.attempt_count += 1
            job.started_at    = datetime.now().isoformat(timespec="seconds")
            job.retry_after   = None
            self._state.update_job(job)

            self._event_bus.publish(Event(
                EventType.WORKFLOW_STARTED,
                {
                    "job_id":     job.job_id,
                    "definition": definition_name,
                    "attempt":    job.attempt_count,
                },
            ))

            wf_status = self._runner.run(definition, context=dict(job.context))
            self._finalize_job(job, wf_status)

            if job.status == JobStatus.PENDING:   # リトライ予約
                time.sleep(job.retry_delay_sec)
                continue
            break

        return job

    # ---- Private: Loop -----------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._tick()
            self._stop_event.wait(timeout=self._poll_sec)
        self._orch_status.running = False
        self._flush_status()

    def _tick(self) -> None:
        """1ループサイクル: 完了確認 → 新規起動 → 状態更新。"""
        self._check_completions()
        self._start_pending_jobs()
        self._update_orch_status()
        self._flush_status()

    def _check_completions(self) -> None:
        """実行中ジョブのワークフロー完了を検出して後処理する。"""
        from src.workflow.enums import WorkflowState
        _TERMINAL = {
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }

        for job in self._state.list_jobs(JobStatus.RUNNING):
            wf_status = self._state.get_active_wf_status(job.job_id)
            if wf_status is not None and wf_status.state in _TERMINAL:
                self._finalize_job(job, wf_status)
                self._state.remove_active_wf_status(job.job_id)

    def _start_pending_jobs(self) -> None:
        """空きスロット数だけ PENDING ジョブを起動する。"""
        running   = self._state.get_running_count()
        available = self._config.max_concurrent_workflows - running
        if available <= 0:
            return

        for job in self._state.get_next_pending_jobs(limit=available):
            self._start_job(job)

    def _start_job(self, job: WorkflowJob) -> None:
        """1ジョブの非同期実行を開始する。"""
        definition = self._registry.get_workflow(job.definition_name)
        if definition is None:
            job.status   = JobStatus.FAILED
            job.error    = f"Workflow が Registry に未登録: {job.definition_name!r}"
            job.ended_at = datetime.now().isoformat(timespec="seconds")
            self._state.update_job(job)
            return

        job.status        = JobStatus.RUNNING
        job.attempt_count += 1
        job.started_at    = datetime.now().isoformat(timespec="seconds")
        job.retry_after   = None
        self._state.update_job(job)

        wf_status       = self._runner.run_async(definition, context=dict(job.context))
        job.workflow_id  = wf_status.workflow_id
        self._state.update_job(job)
        self._state.set_active_wf_status(job.job_id, wf_status)

        self._event_bus.publish(Event(
            EventType.WORKFLOW_STARTED,
            {
                "job_id":      job.job_id,
                "definition":  job.definition_name,
                "workflow_id": wf_status.workflow_id,
                "attempt":     job.attempt_count,
            },
        ))

    def _finalize_job(self, job: WorkflowJob, wf_status: "WorkflowStatus") -> None:
        """
        ワークフロー終了後のジョブ状態を確定する。

        失敗かつリトライ残あり → status=PENDING / retry_after 設定
        失敗かつリトライ上限超 → status=FAILED
        成功                   → status=COMPLETED
        """
        from src.workflow.enums import WorkflowState

        ended_now    = datetime.now()
        job.ended_at = ended_now.isoformat(timespec="seconds")

        if job.started_at:
            try:
                delta        = ended_now - datetime.fromisoformat(job.started_at)
                job.duration_ms = max(0, int(delta.total_seconds() * 1000))
            except Exception:
                pass

        if wf_status.state == WorkflowState.COMPLETED:
            job.status = JobStatus.COMPLETED
            job.error  = None
            self._event_bus.publish(Event(
                EventType.WORKFLOW_FINISHED,
                {
                    "job_id":      job.job_id,
                    "definition":  job.definition_name,
                    "duration_ms": job.duration_ms,
                },
            ))

        elif wf_status.state == WorkflowState.FAILED:
            job.error = wf_status.error
            if job.attempt_count <= job.retry_max:
                retry_at        = ended_now + timedelta(seconds=job.retry_delay_sec)
                job.retry_after = retry_at.isoformat(timespec="seconds")
                job.status      = JobStatus.PENDING   # ループで再起動
                job.started_at  = None
                job.ended_at    = None
            else:
                job.status = JobStatus.FAILED
                self._event_bus.publish(Event(
                    EventType.WORKFLOW_FAILED,
                    {
                        "job_id":        job.job_id,
                        "error":         job.error,
                        "attempt_count": job.attempt_count,
                    },
                ))

        elif wf_status.state == WorkflowState.CANCELLED:
            job.status = JobStatus.CANCELLED
            self._event_bus.publish(Event(
                EventType.WORKFLOW_CANCELLED, {"job_id": job.job_id}
            ))

        self._state.update_job(job)

    # ---- Private: Status & Persistence -------------------------

    def _update_orch_status(self) -> None:
        """OrchestratorStatus を全ジョブから集計する。"""
        all_jobs  = self._state.list_jobs()
        today_str = str(datetime.now().date())

        self._orch_status.total_jobs            = len(all_jobs)
        self._orch_status.active_workflow_count = sum(
            1 for j in all_jobs if j.status == JobStatus.RUNNING
        )
        self._orch_status.pending_job_count = sum(
            1 for j in all_jobs if j.status == JobStatus.PENDING
        )
        self._orch_status.failed_count = sum(
            1 for j in all_jobs if j.status == JobStatus.FAILED
        )
        self._orch_status.completed_today = sum(
            1 for j in all_jobs
            if j.status == JobStatus.COMPLETED
            and str(j.ended_at or "")[:10] == today_str
        )

        completed = [
            j for j in all_jobs
            if j.status == JobStatus.COMPLETED and j.duration_ms > 0
        ]
        self._orch_status.avg_duration_ms = (
            sum(j.duration_ms for j in completed) / len(completed)
            if completed else 0.0
        )

        history = self._event_bus.get_history(limit=1)
        if history:
            last = history[-1]
            self._orch_status.last_event    = last.event_type.value
            self._orch_status.last_event_at = last.timestamp

    def _flush_status(self) -> None:
        """data/orchestrator_status.json へ書き出す。例外は無視する。"""
        try:
            self._status_path.parent.mkdir(parents=True, exist_ok=True)
            save_json_atomic(self._status_path, self._orch_status.to_dict())
        except Exception:
            pass
