from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


COMMANDER_QUEUE_PATH = PROJECT_ROOT / "config" / "commander_queue.json"
STATUS_PENDING = "pending"
STATUS_QUEUED = "queued"
STATUS_RETRY_QUEUED = "retry_queued"
STATUS_DRY_RUN_COMPLETE = "dry_run_complete"
STATUS_APPROVED = "approved"
STATUS_EXECUTE_READY = "execute_ready"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_DEFERRED = "deferred"

ACTIVE_STATUSES = {STATUS_PENDING, STATUS_QUEUED, STATUS_RETRY_QUEUED, STATUS_APPROVED, STATUS_EXECUTE_READY, STATUS_RUNNING}
HISTORY_STATUSES = {STATUS_DRY_RUN_COMPLETE, STATUS_COMPLETED, STATUS_FAILED, STATUS_DEFERRED}
QUEUE_STATUSES = ACTIVE_STATUSES | HISTORY_STATUSES

STATUS_LABELS = {
    STATUS_PENDING: "Pending",
    STATUS_QUEUED: "Pending",
    STATUS_RETRY_QUEUED: "Pending",
    STATUS_DRY_RUN_COMPLETE: "DryRun Complete",
    STATUS_APPROVED: "Approved",
    STATUS_EXECUTE_READY: "Execute Ready",
    STATUS_RUNNING: "Running",
    STATUS_COMPLETED: "Completed",
    STATUS_FAILED: "Failed",
    STATUS_DEFERRED: "Deferred",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "dry_run_default": True,
        "current_job": {},
        "queue": [],
        "history": [],
        "callbacks": [],
        "metrics": [],
        "updated_at": _now(),
    }


class CommanderQueue:
    def __init__(self, path: str | Path = COMMANDER_QUEUE_PATH) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        data = load_json(self.path, default=None)
        if not isinstance(data, dict):
            data = _default_state()
            self.save(data)
        defaults = _default_state()
        for key, value in defaults.items():
            data.setdefault(key, value)
        return data

    def save(self, data: dict[str, Any]) -> None:
        data["updated_at"] = _now()
        save_json_atomic(self.path, data)

    def enqueue(
        self,
        *,
        engine: str,
        instruction: str,
        priority: int = 50,
        callback: dict[str, Any] | None = None,
        dry_run: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        job = {
            "job_id": f"cmd-{uuid4().hex[:10]}",
            "priority": int(priority or 0),
            "engine": engine,
            "instruction": instruction,
            "status": STATUS_PENDING,
            "result": {},
            "dry_run_result": {},
            "diff_preview": {},
            "approved_at": "",
            "approved_by": "",
            "started_at": "",
            "finished_at": "",
            "callback": callback or {"targets": ["business", "mission_planner", "knowledge", "coding_engine"]},
            "dry_run": bool(dry_run),
            "retry_count": 0,
            "max_retries": 2,
            "provider_order": ["claude_cli", "gemini_cli", "openai", "ai_router", "ollama"],
            "metadata": metadata or {},
            "created_at": _now(),
            "updated_at": _now(),
        }
        data = self.load()
        data.setdefault("queue", []).append(job)
        self.save(data)
        return job

    def next_job(self) -> dict[str, Any] | None:
        data = self.load()
        candidates = [job for job in data.get("queue", []) if job.get("status") in {STATUS_PENDING, STATUS_QUEUED, STATUS_RETRY_QUEUED, STATUS_EXECUTE_READY}]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: (-int(item.get("priority", 0)), item.get("created_at", "")))[0]

    def update_job(self, job_id: str, **updates: Any) -> dict[str, Any] | None:
        data = self.load()
        for job in data.get("queue", []):
            if job.get("job_id") == job_id:
                if "status" in updates and updates["status"] not in QUEUE_STATUSES:
                    raise ValueError(f"Unsupported commander status: {updates['status']}")
                job.update(updates)
                job["updated_at"] = _now()
                data["current_job"] = job if job.get("status") == STATUS_RUNNING else {}
                self.save(data)
                return job
        return None

    def finish_job(self, job_id: str, status: str, result: dict[str, Any], *, keep_in_queue: bool = False) -> dict[str, Any] | None:
        if status not in QUEUE_STATUSES:
            raise ValueError(f"Unsupported commander status: {status}")
        data = self.load()
        for index, job in enumerate(list(data.get("queue", []))):
            if job.get("job_id") == job_id:
                job["status"] = status
                job["result"] = result
                if result.get("dry_run"):
                    job["dry_run_result"] = result
                job["diff_preview"] = self.extract_diff_preview(result)
                job["finished_at"] = _now()
                job["updated_at"] = _now()
                if not keep_in_queue:
                    data["queue"].pop(index)
                data.setdefault("history", []).insert(0, job)
                data["history"] = data["history"][:300]
                data["current_job"] = {}
                self.save(data)
                return job
        return None

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        data = self.load()
        for job in data.get("queue", []) + data.get("history", []):
            if job.get("job_id") == job_id:
                return job
        return None

    def approve(self, job_id: str, *, approved_by: str = "human") -> dict[str, Any] | None:
        data = self.load()
        for job in data.get("queue", []):
            if job.get("job_id") == job_id and job.get("status") == STATUS_DRY_RUN_COMPLETE:
                job["status"] = STATUS_APPROVED
                job["approved_by"] = approved_by
                job["approved_at"] = _now()
                job["updated_at"] = _now()
                self.save(data)
                return job
        for index, job in enumerate(list(data.get("history", []))):
            if job.get("job_id") == job_id and job.get("status") == STATUS_DRY_RUN_COMPLETE:
                job["status"] = STATUS_APPROVED
                job["approved_by"] = approved_by
                job["approved_at"] = _now()
                job["updated_at"] = _now()
                data["history"].pop(index)
                data.setdefault("queue", []).append(job)
                self.save(data)
                return job
        return None

    def mark_execute_ready(self, job_id: str) -> dict[str, Any] | None:
        data = self.load()
        for job in data.get("queue", []):
            if job.get("job_id") == job_id and job.get("status") == STATUS_APPROVED:
                job["status"] = STATUS_EXECUTE_READY
                job["dry_run"] = False
                job["apply_approved"] = True
                job["updated_at"] = _now()
                self.save(data)
                return job
        return None

    def summary(self) -> dict[str, Any]:
        data = self.load()
        history = data.get("history", [])
        queue = data.get("queue", [])
        return {
            "current_job": data.get("current_job", {}),
            "queued": len([job for job in queue if job.get("status") in {STATUS_PENDING, STATUS_QUEUED, STATUS_RETRY_QUEUED}]),
            "dry_run_complete": len([job for job in queue + history if job.get("status") == STATUS_DRY_RUN_COMPLETE]),
            "approved": len([job for job in queue + history if job.get("status") == STATUS_APPROVED]),
            "execute_ready": len([job for job in queue if job.get("status") == STATUS_EXECUTE_READY]),
            "running": len([job for job in queue if job.get("status") == STATUS_RUNNING]),
            "completed": len([job for job in history if job.get("status") in {STATUS_COMPLETED, STATUS_DRY_RUN_COMPLETE}]),
            "failed": len([job for job in history if job.get("status") == STATUS_FAILED]),
            "deferred": len([job for job in history if job.get("status") == STATUS_DEFERRED]),
            "status_counts": self.status_counts(queue + history),
            "queue": queue,
            "history": history[:50],
            "metrics": data.get("metrics", [])[:100],
        }

    @staticmethod
    def status_counts(jobs: list[dict[str, Any]]) -> dict[str, int]:
        counts = {status: len([job for job in jobs if job.get("status") == status]) for status in QUEUE_STATUSES}
        counts[STATUS_PENDING] += counts.get(STATUS_QUEUED, 0) + counts.get(STATUS_RETRY_QUEUED, 0)
        return counts

    @staticmethod
    def extract_diff_preview(result: dict[str, Any]) -> dict[str, Any]:
        applied = result.get("coding_run", {}).get("applied_edits", {})
        preview = applied.get("preview", {}) if isinstance(applied, dict) else {}
        return {
            "status": applied.get("status", "") if isinstance(applied, dict) else "",
            "target_files": preview.get("target_files", []),
            "unified_diff": preview.get("unified_diff", ""),
            "requires_approval": bool(preview.get("requires_approval", False)),
        }
