from __future__ import annotations

from pathlib import Path
from typing import Any

from src.commander.queue import CommanderQueue
from src.commander.templates import get_template, list_templates
from src.commander.worker import CommanderWorker
from src.utils.config import PROJECT_ROOT


class CommanderAPI:
    """Internal Commander API surface matching /api/commander/* actions."""

    def __init__(self, queue: CommanderQueue | None = None, *, root: str | Path = PROJECT_ROOT, worker: CommanderWorker | None = None) -> None:
        self.queue = queue or CommanderQueue()
        self.root = Path(root)
        self.worker = worker or CommanderWorker(self.queue, root=self.root)

    def queue_endpoint(self) -> dict[str, Any]:
        """GET /api/commander/queue."""
        summary = self.queue.summary()
        return {
            "ok": True,
            "endpoint": "/api/commander/queue",
            "queue": summary.get("queue", []),
            "status_counts": summary.get("status_counts", {}),
            "templates": list_templates(),
        }

    def history_endpoint(self) -> dict[str, Any]:
        """GET /api/commander/history."""
        summary = self.queue.summary()
        return {
            "ok": True,
            "endpoint": "/api/commander/history",
            "history": summary.get("history", []),
            "metrics": summary.get("metrics", []),
        }

    def enqueue_template(self, template_id: str, *, dry_run: bool = True) -> dict[str, Any]:
        template = get_template(template_id)
        if template is None:
            return {"ok": False, "error": f"Unknown commander template: {template_id}"}
        job = self.queue.enqueue(
            engine=template["engine"],
            instruction=template["instruction"],
            priority=template["priority"],
            dry_run=dry_run,
            metadata={"target_files": template["target_files"], "pytest_args": ["-q"]},
            callback={"targets": ["business", "revenue", "growth", "mission_planner", "knowledge", "coding_engine"]},
        )
        job = self.queue.update_job(job["job_id"], template_id=template_id) or job
        return {"ok": True, "job": job}

    def approve_endpoint(self, job_id: str, *, approved_by: str = "human") -> dict[str, Any]:
        """POST /api/commander/approve."""
        job = self.queue.approve(job_id, approved_by=approved_by)
        if not job:
            return {"ok": False, "endpoint": "/api/commander/approve", "error": "Job is not ready for approval."}
        return {"ok": True, "endpoint": "/api/commander/approve", "job": job}

    def execute_endpoint(self, job_id: str) -> dict[str, Any]:
        """POST /api/commander/execute."""
        ready = self.queue.mark_execute_ready(job_id)
        if not ready:
            return {"ok": False, "endpoint": "/api/commander/execute", "error": "Job must be approved before execute."}
        result = self.worker.process_job(ready, dry_run=False)
        return {"ok": result.get("status") == "completed", "endpoint": "/api/commander/execute", "result": result}
