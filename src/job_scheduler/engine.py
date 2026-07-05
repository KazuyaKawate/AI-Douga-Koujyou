"""JobEngine — ScheduledJob を時間起動・手動実行するエンジン。

from src.utils.json_store import save_json_atomic
Kernel / Router / Memory 変更なし。
kernel.orchestrator.run_workflow() を呼び出すだけ。
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .job import JobRunRecord, JobStatus, ScheduledJob, TriggerConfig, TriggerType

_JOBS_FILE  = Path("data/job_scheduler/jobs.json")
_TICK_SEC   = 30.0   # 30秒ごとにジョブチェック
_lock       = threading.Lock()
_instance: Optional["JobEngine"] = None


class JobEngine:
    """
    GUI 向け Workflow スケジューラー。

    機能:
        add_job(job)         — ジョブ追加
        remove_job(job_id)   — ジョブ削除
        run_now(job_id)      — 手動即時実行
        pause(job_id)        — 一時停止
        resume(job_id)       — 再開
        list_jobs()          — 一覧取得（GUI 表示用）
        start()              — バックグラウンドスレッドで自動実行開始
        stop()               — 停止

    永続化: data/job_scheduler/jobs.json
    """

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._load()

    # ── Job CRUD ─────────────────────────────────────────────────

    def add_job(self, job: ScheduledJob) -> ScheduledJob:
        """ジョブを追加し次回実行時刻を計算する。"""
        job.next_run_at = self._calc_next(job.trigger)
        with _lock:
            self._jobs[job.job_id] = job
            self._save()
        return job

    def remove_job(self, job_id: str) -> bool:
        with _lock:
            if job_id not in self._jobs:
                return False
            del self._jobs[job_id]
            self._save()
        return True

    def pause(self, job_id: str) -> bool:
        with _lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            job.status = JobStatus.PAUSED
            self._save()
        return True

    def resume(self, job_id: str) -> bool:
        with _lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            job.status     = JobStatus.ACTIVE
            job.next_run_at= self._calc_next(job.trigger)
            self._save()
        return True

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[ScheduledJob]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def count(self) -> int:
        return len(self._jobs)

    # ── 手動実行 ─────────────────────────────────────────────────

    def run_now(self, job_id: str) -> JobRunRecord:
        """指定ジョブを同期実行する。GUI の「今すぐ実行」ボタン用。"""
        job = self._jobs.get(job_id)
        if not job:
            return JobRunRecord(
                started_at=datetime.now().isoformat(timespec="seconds"),
                success=False,
                error=f"Job not found: {job_id}",
            )
        return self._execute(job)

    # ── バックグラウンドスレッド ──────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="JobEngine"
        )
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Private: ループ ───────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._check_and_run()
            self._stop_event.wait(timeout=_TICK_SEC)

    def _check_and_run(self) -> None:
        now = datetime.now()
        with _lock:
            jobs = list(self._jobs.values())
        for job in jobs:
            if job.status != JobStatus.ACTIVE:
                continue
            if not job.next_run_at:
                continue
            try:
                next_dt = datetime.fromisoformat(job.next_run_at)
            except Exception:
                continue
            if now >= next_dt:
                self._execute(job)
                with _lock:
                    if job.trigger.type == TriggerType.ONCE:
                        job.status = JobStatus.FINISHED
                    else:
                        job.next_run_at = self._calc_next(job.trigger)
                    self._save()

    # ── Private: 実行 ────────────────────────────────────────────

    def _execute(self, job: ScheduledJob) -> JobRunRecord:
        started_at = datetime.now().isoformat(timespec="seconds")
        t0         = time.monotonic()
        success    = True
        error_msg  = None

        try:
            from src.core.kernel import get_kernel
            kernel = get_kernel()
            wf_status = kernel.run_workflow(job.workflow_name, job.context.copy())
            success   = wf_status.success if hasattr(wf_status, "success") else True

            # ExecutionTracker に記録
            try:
                from src.intelligence.tracker import get_tracker
                get_tracker().record(
                    workflow_name=job.workflow_name,
                    factory_id=job.workflow_name.split(".")[0],
                    success=success,
                    duration_ms=int((time.monotonic() - t0) * 1000),
                )
            except Exception:
                pass

        except Exception as exc:
            success   = False
            error_msg = str(exc)

        rec = JobRunRecord(
            started_at  = started_at,
            ended_at    = datetime.now().isoformat(timespec="seconds"),
            success     = success,
            duration_ms = int((time.monotonic() - t0) * 1000),
            error       = error_msg,
        )

        with _lock:
            job.run_count  += 1
            job.last_run_at = started_at
            job.updated_at  = datetime.now().isoformat(timespec="seconds")
            job.run_history.append(rec)
            if not success:
                job.status = JobStatus.FAILED
            self._save()

        return rec

    # ── Private: 次回実行計算 ─────────────────────────────────────

    @staticmethod
    def _calc_next(trigger: TriggerConfig) -> Optional[str]:
        now = datetime.now()
        t   = trigger.type

        if t == TriggerType.ONCE:
            return trigger.run_once_at

        if t == TriggerType.MANUAL or t == TriggerType.WEBHOOK:
            return None

        if t == TriggerType.INTERVAL and trigger.interval_min:
            nxt = now + timedelta(minutes=trigger.interval_min)
            return nxt.isoformat(timespec="seconds")

        if t in (TriggerType.DAILY, TriggerType.WEEKLY) and trigger.run_at:
            h, m   = map(int, trigger.run_at.split(":"))
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)

            if t == TriggerType.DAILY:
                if target <= now:
                    target += timedelta(days=1)
                return target.isoformat(timespec="seconds")

            if t == TriggerType.WEEKLY and trigger.weekday is not None:
                days_ahead = (trigger.weekday - now.weekday()) % 7
                if days_ahead == 0 and target <= now:
                    days_ahead = 7
                target += timedelta(days=days_ahead)
                return target.isoformat(timespec="seconds")

        return None

    # ── Private: 永続化 ──────────────────────────────────────────

    def _load(self) -> None:
        if not _JOBS_FILE.exists():
            return
        try:
            raw = json.loads(_JOBS_FILE.read_text(encoding="utf-8"))
            for jid, d in raw.get("jobs", {}).items():
                self._jobs[jid] = ScheduledJob.from_dict(d)
        except Exception:
            pass

    def _save(self) -> None:
        _JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"jobs": {jid: j.to_dict() for jid, j in self._jobs.items()}}
        save_json_atomic(_JOBS_FILE, data)

    # ── ファクトリ関数 ────────────────────────────────────────────

    @staticmethod
    def create_job(
        name:          str,
        workflow_name: str,
        trigger_type:  TriggerType     = TriggerType.MANUAL,
        context:       dict            = None,
        run_at:        Optional[str]   = None,   # "HH:MM"
        weekday:       Optional[int]   = None,
        interval_min:  Optional[int]   = None,
        run_once_at:   Optional[str]   = None,
    ) -> ScheduledJob:
        """ScheduledJob を生成するヘルパー。"""
        return ScheduledJob(
            job_id        = str(uuid.uuid4())[:8],
            name          = name,
            workflow_name = workflow_name,
            context       = dict(context or {}),
            trigger       = TriggerConfig(
                type         = trigger_type,
                run_at       = run_at,
                weekday      = weekday,
                interval_min = interval_min,
                run_once_at  = run_once_at,
            ),
        )


def get_job_engine() -> JobEngine:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = JobEngine()
    return _instance
