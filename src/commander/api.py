from __future__ import annotations

from pathlib import Path
from typing import Any

from src.commander.queue import CommanderQueue
from src.commander.content_operation import ContentOperationEngine
from src.commander.execution_engine import ExecutionEngine
from src.commander.planner import CommanderPlanner
from src.commander.templates import get_template, list_templates
from src.commander.worker import CommanderWorker
from src.utils.config import PROJECT_ROOT


class CommanderAPI:
    """Internal Commander API surface matching /api/commander/* actions."""

    def __init__(self, queue: CommanderQueue | None = None, *, root: str | Path = PROJECT_ROOT, worker: CommanderWorker | None = None) -> None:
        self.queue = queue or CommanderQueue()
        self.root = Path(root)
        self.worker = worker or CommanderWorker(self.queue, root=self.root)
        self.planner = CommanderPlanner()
        self.content = ContentOperationEngine(self.root)
        self.execution = ExecutionEngine(self.root)

    def queue_endpoint(self) -> dict[str, Any]:
        """GET /api/commander/queue."""
        summary = self.queue.summary()
        return {
            "ok": True,
            "endpoint": "/api/commander/queue",
            "queue": summary.get("queue", []),
            "business_queue": summary.get("business_queue", []),
            "dashboard": summary.get("dashboard", {}),
            "executive": summary.get("executive", {}),
            "company": summary.get("company", {}),
            "content_operation": summary.get("content_operation", {}),
            "execution": summary.get("execution", {}),
            "revenue_plan": summary.get("revenue_plan", {}),
            "revenue_engine": summary.get("revenue_engine", {}),
            "growth_engine": summary.get("growth_engine", {}),
            "employee_queues": summary.get("employee_queues", {}),
            "knowledge_growth": summary.get("knowledge_growth", {}),
            "ceo_meeting": summary.get("ceo_meeting", {}),
            "self_company": summary.get("self_company", {}),
            "system_health": summary.get("system_health", {}),
            "status_counts": summary.get("status_counts", {}),
            "templates": list_templates(),
        }

    def create_content_draft(
        self,
        channel: str,
        instruction: str,
        *,
        expected_revenue: int = 0,
        target: str = "初収益",
    ) -> dict[str, Any]:
        item = self.content.create_draft(channel=channel, instruction=instruction, expected_revenue=expected_revenue, target=target)
        return {"ok": item.get("status") != "rejected", "content": item}

    def approve_content(self, content_id: str, *, review_notes: str = "") -> dict[str, Any]:
        item = self.content.approve(content_id, review_notes=review_notes)
        if not item:
            return {"ok": False, "error": "Content is not ready for approval."}
        return {"ok": True, "content": item}

    def create_execution_action(self, task: dict[str, Any], *, channel: str | None = None) -> dict[str, Any]:
        action = self.execution.create_action_from_task(task, channel=channel)
        return {"ok": True, "action": action}

    def approve_execution(self, action_id: str, *, review_notes: str = "") -> dict[str, Any]:
        action = self.execution.approve(action_id, review_notes=review_notes)
        if not action:
            return {"ok": False, "error": "Action is not ready for approval."}
        return {"ok": True, "action": action}

    def schedule_execution(self, action_id: str) -> dict[str, Any]:
        return self.execution.schedule(action_id)

    def publish_execution(self, action_id: str) -> dict[str, Any]:
        return self.execution.publish(action_id)

    def retry_execution(self, action_id: str) -> dict[str, Any]:
        return self.execution.retry(action_id)

    def history_endpoint(self) -> dict[str, Any]:
        """GET /api/commander/history."""
        summary = self.queue.summary()
        return {
            "ok": True,
            "endpoint": "/api/commander/history",
            "history": summary.get("history", []),
            "metrics": summary.get("metrics", []),
            "history_metrics": summary.get("history_metrics", {}),
            "knowledge_growth": summary.get("knowledge_growth", {}),
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
        plan = self.planner.build_plan(template["instruction"], {"target_files": template["target_files"]})
        job = self.queue.update_job(job["job_id"], template_id=template_id, plan=plan, business_task=plan["business_task"]) or job
        return {"ok": True, "job": job}

    def enqueue_instruction(
        self,
        instruction: str,
        *,
        engine: str | None = None,
        priority: int = 80,
        target_files: list[str] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Create a Commander job from natural language and save its plan."""
        plan = self.planner.build_plan(instruction, {"target_files": target_files or []})
        job = self.queue.enqueue(
            engine=engine or plan.get("engine", "coding_engine"),
            instruction=instruction,
            priority=priority,
            dry_run=True if dry_run is None else bool(dry_run),
            metadata={"target_files": plan.get("impacted_files", []), "pytest_args": ["-q"]},
            callback={"targets": plan.get("callback_targets", [])},
        )
        job = self.queue.update_job(job["job_id"], plan=plan, business_task=plan["business_task"], approval_required=True, execute_allowed=False) or job
        return {"ok": True, "job": job, "plan": plan}

    def approve_endpoint(self, job_id: str, *, approved_by: str = "human") -> dict[str, Any]:
        """POST /api/commander/approve."""
        job = self.queue.approve(job_id, approved_by=approved_by)
        if not job:
            return {"ok": False, "endpoint": "/api/commander/approve", "error": "Job is not ready for approval."}
        return {"ok": True, "endpoint": "/api/commander/approve", "job": job}

    def reject_endpoint(self, job_id: str, *, reason: str = "", rejected_by: str = "human") -> dict[str, Any]:
        """POST /api/commander/reject."""
        job = self.queue.reject(job_id, rejected_by=rejected_by, reason=reason)
        if not job:
            return {"ok": False, "endpoint": "/api/commander/reject", "error": "Job not found."}
        return {"ok": True, "endpoint": "/api/commander/reject", "job": job}

    def execute_endpoint(self, job_id: str) -> dict[str, Any]:
        """POST /api/commander/execute."""
        ready = self.queue.mark_execute_ready(job_id)
        if not ready:
            return {"ok": False, "endpoint": "/api/commander/execute", "error": "Job must be approved before execute."}
        result = self.worker.process_job(ready, dry_run=False)
        return {"ok": result.get("status") == "completed", "endpoint": "/api/commander/execute", "result": result}
