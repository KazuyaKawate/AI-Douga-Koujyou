from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic
from src.commander.autonomous_company import AutonomousCompanyEngine
from src.commander.company_engine import CompanyEngine
from src.commander.content_operation import ContentOperationEngine
from src.commander.execution_engine import ExecutionEngine
from src.commander.knowledge_engine import CommanderKnowledgeEngine
from src.commander.revenue_planner import CommanderRevenuePlanner


COMMANDER_QUEUE_PATH = PROJECT_ROOT / "config" / "commander_queue.json"
STATUS_WAITING = "waiting"
STATUS_PLANNING = "planning"
STATUS_RETRY_QUEUED = "retry_queued"
STATUS_DRY_RUN_COMPLETED = "dry_run_completed"
STATUS_APPROVED = "approved"
STATUS_EXECUTE_READY = "execute_ready"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_DEFERRED = "deferred"
STATUS_REJECTED = "rejected"

# Backward-compatible names used by older tests and callbacks.
STATUS_PENDING = STATUS_WAITING
STATUS_QUEUED = STATUS_WAITING
STATUS_DRY_RUN_COMPLETE = STATUS_DRY_RUN_COMPLETED

ACTIVE_STATUSES = {STATUS_WAITING, STATUS_PLANNING, STATUS_RETRY_QUEUED, STATUS_APPROVED, STATUS_EXECUTE_READY, STATUS_RUNNING}
HISTORY_STATUSES = {STATUS_DRY_RUN_COMPLETED, STATUS_COMPLETED, STATUS_FAILED, STATUS_DEFERRED, STATUS_REJECTED}
QUEUE_STATUSES = ACTIVE_STATUSES | HISTORY_STATUSES

STATUS_LABELS = {
    STATUS_WAITING: "Waiting",
    STATUS_PLANNING: "Planning",
    STATUS_RETRY_QUEUED: "Pending",
    STATUS_DRY_RUN_COMPLETED: "DryRun Completed",
    STATUS_APPROVED: "Approved",
    STATUS_EXECUTE_READY: "Execute Ready",
    STATUS_RUNNING: "Running",
    STATUS_COMPLETED: "Completed",
    STATUS_FAILED: "Failed",
    STATUS_DEFERRED: "Deferred",
    STATUS_REJECTED: "Rejected",
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
            "status": STATUS_WAITING,
            "plan": {},
            "business_task": (metadata or {}).get("business_task", {}),
            "result": {},
            "dry_run_result": {},
            "diff_preview": {},
            "guard": {},
            "approval_required": True,
            "execute_allowed": False,
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
        candidates = [job for job in data.get("queue", []) if job.get("status") in {STATUS_WAITING, STATUS_RETRY_QUEUED, STATUS_EXECUTE_READY}]
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
                if result.get("business_task"):
                    job["business_task"] = result["business_task"]
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
                job["execute_allowed"] = True
                job["updated_at"] = _now()
                self.save(data)
                return job
        for index, job in enumerate(list(data.get("history", []))):
            if job.get("job_id") == job_id and job.get("status") == STATUS_DRY_RUN_COMPLETE:
                job["status"] = STATUS_APPROVED
                job["approved_by"] = approved_by
                job["approved_at"] = _now()
                job["execute_allowed"] = True
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
                job["execute_allowed"] = True
                job["updated_at"] = _now()
                self.save(data)
                return job
        return None

    def reject(self, job_id: str, *, rejected_by: str = "human", reason: str = "") -> dict[str, Any] | None:
        data = self.load()
        for source in ("queue", "history"):
            for index, job in enumerate(list(data.get(source, []))):
                if job.get("job_id") != job_id:
                    continue
                job["status"] = STATUS_REJECTED
                job["rejected_by"] = rejected_by
                job["rejected_reason"] = reason
                job["execute_allowed"] = False
                job["updated_at"] = _now()
                if source == "queue":
                    data["queue"].pop(index)
                else:
                    data["history"].pop(index)
                data.setdefault("history", []).insert(0, job)
                data["current_job"] = {}
                self.save(data)
                return job
        return None

    def summary(self) -> dict[str, Any]:
        data = self.load()
        history = data.get("history", [])
        queue = data.get("queue", [])
        business_queue = self.business_queue(queue)
        history_metrics = self.history_metrics(history)
        revenue_plan = CommanderRevenuePlanner(self.path.parent.parent).update_daily(business_queue, history_metrics)
        company = CompanyEngine(self.path.parent.parent).update(revenue_plan)
        knowledge_growth = CommanderKnowledgeEngine(self.path.parent.parent).growth_summary()
        pending_review = [job for job in queue + history if job.get("status") in {STATUS_DRY_RUN_COMPLETED, STATUS_APPROVED}]
        executive_next = business_queue[0] if business_queue else None
        autonomous = AutonomousCompanyEngine(self.path.parent.parent)
        content_operation = ContentOperationEngine(self.path.parent.parent).summary()
        execution = ExecutionEngine(self.path.parent.parent).summary()
        revenue_engine = autonomous.revenue_engine(business_queue)
        growth_engine = autonomous.growth_engine()
        employee_queues = autonomous.employee_queues(business_queue)
        self_company = autonomous.self_company_cycle()
        return {
            "current_job": data.get("current_job", {}),
            "queued": len([job for job in queue if job.get("status") in {STATUS_WAITING, STATUS_RETRY_QUEUED}]),
            "planning": len([job for job in queue if job.get("status") == STATUS_PLANNING]),
            "dry_run_complete": len([job for job in queue + history if job.get("status") == STATUS_DRY_RUN_COMPLETED]),
            "approved": len([job for job in queue + history if job.get("status") == STATUS_APPROVED]),
            "execute_ready": len([job for job in queue if job.get("status") == STATUS_EXECUTE_READY]),
            "running": len([job for job in queue if job.get("status") == STATUS_RUNNING]),
            "completed": len([job for job in history if job.get("status") in {STATUS_COMPLETED, STATUS_DRY_RUN_COMPLETE}]),
            "failed": len([job for job in history if job.get("status") == STATUS_FAILED]),
            "deferred": len([job for job in history if job.get("status") == STATUS_DEFERRED]),
            "rejected": len([job for job in history if job.get("status") == STATUS_REJECTED]),
            "status_counts": self.status_counts(queue + history),
            "queue": queue,
            "history": history[:50],
            "metrics": data.get("metrics", [])[:100],
            "business_queue": business_queue,
            "dashboard": {
                "today": [job for job in business_queue if job.get("business_task", {}).get("deadline") == "today"],
                "this_week": [job for job in business_queue if job.get("business_task", {}).get("deadline") in {"today", "this_week"}],
                "revenue_queue": business_queue,
                "completed": [job for job in history if job.get("status") == STATUS_COMPLETED],
                "failed": [job for job in history if job.get("status") in {STATUS_FAILED, STATUS_REJECTED}],
                "pending_review": pending_review,
            },
            "executive": {
                "next_action": executive_next,
                "top_priority": executive_next,
                "top3": business_queue[:3],
                "this_week": business_queue[:3],
                "this_month": business_queue[:5],
                "message": self.executive_message(executive_next),
            },
            "history_metrics": history_metrics,
            "company": company,
            "content_operation": content_operation,
            "execution": execution,
            "revenue_plan": revenue_plan,
            "revenue_engine": revenue_engine,
            "growth_engine": growth_engine,
            "employee_queues": employee_queues,
            "knowledge_growth": knowledge_growth,
            "ceo_meeting": autonomous.meeting_reports(
                {
                    "dashboard": {"today": [job for job in business_queue if job.get("business_task", {}).get("deadline") == "today"]},
                    "history_metrics": history_metrics,
                    "revenue_plan": revenue_plan,
                    "system_health": {"status": "attention" if pending_review else "ok"},
                }
            ),
            "self_company": self_company,
            "system_health": {
                "queue_ok": True,
                "pending_review": len(pending_review),
                "failed": len([job for job in history if job.get("status") in {STATUS_FAILED, STATUS_REJECTED}]),
                "status": "attention" if pending_review else "ok",
            },
        }

    @staticmethod
    def business_queue(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for job in queue:
            task = job.get("business_task") or job.get("plan", {}).get("business_task", {})
            if not task:
                continue
            rows.append({**job, "business_task": task})
        return sorted(
            rows,
            key=lambda job: (
                -float(job.get("business_task", {}).get("priority_score", 0)),
                -float(job.get("business_task", {}).get("roi", 0)),
                float(job.get("business_task", {}).get("expected_time", 999)),
                job.get("created_at", ""),
            ),
        )

    @staticmethod
    def history_metrics(history: list[dict[str, Any]]) -> dict[str, Any]:
        completed = [job for job in history if job.get("status") == STATUS_COMPLETED]
        failed = [job for job in history if job.get("status") in {STATUS_FAILED, STATUS_REJECTED}]
        tasks = [job.get("business_task") or job.get("plan", {}).get("business_task", {}) for job in history]
        tasks = [task for task in tasks if task]
        total = len(completed) + len(failed)
        return {
            "completed_count": len(completed),
            "failed_count": len(failed),
            "success_rate": round(len(completed) / total, 3) if total else 0,
            "cumulative_expected_revenue": sum(int(task.get("expected_income", task.get("expected_revenue", 0)) or 0) for task in tasks),
            "expected_work_hours": round(sum(float(task.get("expected_time", 0) or 0) for task in tasks), 2),
        }

    @staticmethod
    def executive_message(job: dict[str, Any] | None) -> str:
        if not job:
            return "今AIOSが最優先でやる仕事: Revenue Queueへnote/Threads/Website改善を1件追加する"
        task = job.get("business_task", {})
        title = task.get("title") or job.get("instruction", "")
        return f"今AIOSが最優先でやる仕事: {title}"

    @staticmethod
    def status_counts(jobs: list[dict[str, Any]]) -> dict[str, int]:
        counts = {status: len([job for job in jobs if job.get("status") == status]) for status in QUEUE_STATUSES}
        counts[STATUS_WAITING] += counts.get(STATUS_RETRY_QUEUED, 0)
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
