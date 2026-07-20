from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.commander.queue import CommanderQueue
from src.commander.content_operation import ContentOperationEngine
from src.commander.execution_engine import ExecutionEngine
from src.commander.monetization_flow import CommanderMonetizationFlow
from src.commander.planner import CommanderPlanner
from src.commander.templates import get_template, list_templates
from src.commander.worker import CommanderWorker
from src.utils.config import PROJECT_ROOT
from src.workspace.google_workspace import GoogleWorkspaceManager
from src.workspace.integration import GoogleWorkspaceIntegration
from src.note_workspace import NoteWorkspace
from src.mobile_review_hub import CommonPublishQueue
from src.publish_engine.threads_workflow import ThreadsPublishingWorkflow
from src.commander.chat_store import safe_chat_context
from src.commander.sales_router import CommanderSalesRouter
from src.publish_engine.gateway import PublishEngineGateway
from src.sales_engine.models import SalesValidationError


_SALES_ERROR_SAFETY = {
    "execute_allowed": False,
    "approval_required": True,
    "review_required": True,
    "dry_run": True,
    "production_actions_enabled": False,
    "external_request_sent": False,
}
_SENSITIVE_ERROR_VALUE = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret|authorization|credentials?)\b"
    r"(\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)|"
    r"\bbearer\s+[^\s,;]+"
)


def _sanitize_sales_validation_error(error: SalesValidationError) -> str:
    """Mask credential-like values while preserving useful validation details."""
    message = str(error)

    def redact(match: re.Match[str]) -> str:
        if match.group(1):
            return f"{match.group(1)}{match.group(2)}[REDACTED]"
        return "Bearer [REDACTED]"

    return _SENSITIVE_ERROR_VALUE.sub(redact, message)


class CommanderAPI:
    """Internal Commander API surface matching /api/commander/* actions."""

    def __init__(self, queue: CommanderQueue | None = None, *, root: str | Path = PROJECT_ROOT, worker: CommanderWorker | None = None) -> None:
        self.queue = queue or CommanderQueue()
        self.root = Path(root)
        self.worker = worker or CommanderWorker(self.queue, root=self.root)
        self.planner = CommanderPlanner()
        self.content = ContentOperationEngine(self.root)
        self.execution = ExecutionEngine(self.root)
        self.monetization = CommanderMonetizationFlow(root=self.root)
        self.note_workspace = NoteWorkspace(root=self.root)
        self.mobile_review = CommonPublishQueue(self.root / "data" / "mobile_publish_queue.json")
        self.threads_workflow = ThreadsPublishingWorkflow(root=self.root, queue=self.mobile_review)
        self.publish_gateway = PublishEngineGateway(root=self.root, queue=self.mobile_review, threads=self.threads_workflow, note_workspace=self.note_workspace)
        self.sales_router = CommanderSalesRouter()

    def create_sales_plan_endpoint(
        self,
        instruction: str,
        request: dict[str, Any] | None = None,
        *,
        commercial_terms: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Commander Chat -> Sales planning -> Review Package -> stop."""
        try:
            return self.sales_router.route(instruction, request, commercial_terms=commercial_terms)
        except SalesValidationError as exc:
            return {
                "ok": False,
                "error": _sanitize_sales_validation_error(exc),
                "error_type": "validation_error",
                **_SALES_ERROR_SAFETY,
            }
        except Exception:
            return {
                "ok": False,
                "error": "Unable to create sales plan.",
                "error_type": "internal_error",
                **_SALES_ERROR_SAFETY,
            }

    def mobile_review_queue_endpoint(self) -> dict[str, Any]:
        rows = self.mobile_review.mobile_rows()
        return {"ok": True, "message": f"Mobile Review Hubに{len(rows)}件あります。", "items": rows,
                "dry_run": True, "review_required": True, "production_actions_enabled": False, "execute_allowed": False}

    def commander_chat_context_endpoint(self, job_id: str = "") -> dict[str, Any]:
        """Read-only context for the Phase 107 Commander Chat review panels."""
        job = self.queue.get_job(job_id) if job_id else None
        mobile_rows = self.mobile_review.mobile_rows()
        approval_rows = [row for row in mobile_rows if row.get("status") in {"review_required", "changes_requested", "approved", "ready_to_publish"}]
        plan = (job or {}).get("plan", {})
        engine = (job or {}).get("engine", "commander")
        route = ["commander", engine]
        callback_targets = (job or {}).get("callback", {}).get("targets", [])
        route.extend(target for target in callback_targets if target not in route)
        return safe_chat_context({
            "ok": True,
            "job_id": job_id,
            "workflow_preview": {
                "status": (job or {}).get("status", "waiting" if job_id else "idle"),
                "steps": plan.get("steps", []),
                "impacted_files": plan.get("impacted_files", []),
                "diff_preview": (job or {}).get("diff_preview", {}),
            },
            "engine_routing": {"selected": engine, "route": route},
            "dry_run_result": (job or {}).get("dry_run_result") or (job or {}).get("result") or {},
            "approval_queue": approval_rows[:20],
            "mobile_review_hub": {"count": len(mobile_rows), "items": mobile_rows[:10]},
            "common_publish_queue": {"count": len(mobile_rows), "status": "local_review_only"},
            "google_workspace": GoogleWorkspaceManager(root=self.root).configuration_status(),
            "revenue_engine": self.queue.summary().get("revenue_engine", {}),
        })

    def enqueue_mobile_review_endpoint(self, *, target_platform: str, source_id: str, **payload: Any) -> dict[str, Any]:
        item = self.mobile_review.add(target_platform=target_platform, source_id=source_id, **payload)
        return {"ok": True, "message": "Mobile Review Hubへ追加しました。外部送信は行いません。", "item": item}

    def create_threads_post_endpoint(self, instruction: str, *, target_account: str, **metadata: Any) -> dict[str, Any]:
        """Commander -> Content Engine -> Review Hub -> Publish Engine."""
        created = self.publish_gateway.create_threads_review(instruction, target_account=target_account, **metadata)
        return {"ok": True, **created}

    def dry_run_threads_post_endpoint(self, queue_id: str) -> dict[str, Any]:
        """Approved MobileReviewHub item -> official Threads publisher DryRun."""
        return {"ok": True, **self.publish_gateway.dry_run_reviewed(queue_id)}

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
            "google_workspace": GoogleWorkspaceManager(root=self.root).configuration_status(),
            "monetization": self.monetization.summary(),
        }

    def google_workspace_connection_endpoint(self, *, dry_run: bool = True) -> dict[str, Any]:
        """POST /api/commander/google-workspace/check (read-only, DryRun only)."""
        return GoogleWorkspaceManager(root=self.root).check_connections(dry_run=dry_run)

    def google_save_article_endpoint(self, *, title: str, content: str, folder_id: str = "root") -> dict[str, Any]:
        """Commander -> Review -> Workspace. Always stops before Google write."""
        return GoogleWorkspaceIntegration(root=self.root).commander_save_article(title=title, content=content, folder_id=folder_id)

    def google_workspace_review_endpoint(self, action_id: str, *, approved: bool, reviewer: str = "human") -> dict[str, Any]:
        return GoogleWorkspaceIntegration(root=self.root).review(action_id, approved=approved, reviewer=reviewer)

    def create_note_article_endpoint(self, instruction: str, **workspace_fields: Any) -> dict[str, Any]:
        """Commander phrase `note記事を書いて` -> generated article -> Review Queue."""
        created = self.publish_gateway.create_note_review(instruction, **workspace_fields)
        return {"ok": True, **created, "production_actions_enabled": False}

    def approve_note_article_endpoint(self, article_id: str, *, approver: str) -> dict[str, Any]:
        return {"ok": True, "article": self.note_workspace.approve(article_id, approver=approver)}

    def prepare_note_article_endpoint(self, article_id: str) -> dict[str, Any]:
        return {"ok": True, "article": self.note_workspace.prepare_draft(article_id)}

    def prepare_note_release_endpoint(self, article_id: str, **source: str) -> dict[str, Any]:
        return {"ok": True, "message": "note公開パッケージをLocal Firstで生成しました。本番投稿は行いません。", "package": self.note_workspace.generate_release_package(article_id, **source), "production_actions_enabled": False}

    def prepare_latest_note_release_endpoint(self, **source: str) -> dict[str, Any]:
        article = next((row for row in self.note_workspace.summary()["articles"] if row.get("approval", {}).get("status") == "approved"), None)
        if not article: return {"ok": False, "message": "承認済みnote記事がありません。Review Queueで承認してください。"}
        return self.prepare_note_release_endpoint(article["article_id"], **source)

    def record_note_publish_endpoint(self, article_id: str, **record: Any) -> dict[str, Any]:
        return {"ok": True, "message": "人間が公開したnote記事の事実を登録しました。外部送信は行っていません。", "article": self.note_workspace.record_manual_publish(article_id, **record), "production_actions_enabled": False}

    def record_note_kpi_endpoint(self, article_id: str, **metric: Any) -> dict[str, Any]:
        return {"ok": True, "message": "note実績を手動登録しました。未取得と0は区別して保存しています。", "metric": self.note_workspace.record_kpi(article_id, **metric)}

    def create_monetization_package_endpoint(self, *, instruction: str, cta_url: str = "") -> dict[str, Any]:
        """Stage 1: create note/Threads drafts, review, and stop for a human."""
        return self.monetization.create_and_review(instruction=instruction, cta_url=cta_url)

    def approve_monetization_package_endpoint(self, workflow_id: str, *, approver: str) -> dict[str, Any]:
        """Record explicit human approval with immutable content hashes."""
        return self.monetization.approve(workflow_id, approver=approver)

    def dry_run_monetization_package_endpoint(self, workflow_id: str) -> dict[str, Any]:
        """Stage 2: local-only Dry Run. Live publishing is structurally disabled."""
        return self.monetization.dry_run_publish(workflow_id)

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
