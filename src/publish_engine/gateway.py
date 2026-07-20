from __future__ import annotations

from pathlib import Path
from typing import Any

from src.mobile_review_hub.queue import CommonPublishQueue
from src.publish_engine.threads_workflow import ThreadsPublishingWorkflow
from src.utils.config import PROJECT_ROOT

SAFETY = {"local_first": True, "dry_run": True, "review_required": True, "approval_required": True, "execute_allowed": False, "production_actions_enabled": False, "external_request_sent": False}


class PublishEngineGateway:
    """Single RC2 entry reusing the existing queue and platform workflows."""

    def __init__(self, *, root: str | Path = PROJECT_ROOT, queue: CommonPublishQueue | None = None, threads: ThreadsPublishingWorkflow | None = None, note_workspace: Any = None) -> None:
        self.root = Path(root)
        self.queue = queue or CommonPublishQueue(self.root / "data" / "mobile_publish_queue.json")
        self.threads = threads or ThreadsPublishingWorkflow(root=self.root, queue=self.queue)
        self.note_workspace = note_workspace

    def create_note_review(self, instruction: str, **fields: Any) -> dict[str, Any]:
        if self.note_workspace is None:
            raise RuntimeError("NoteWorkspace adapter is not configured")
        article = self.note_workspace.create(instruction=instruction, **fields)
        reviewed = self.note_workspace.review(article["article_id"])
        return {"article": reviewed, "route": ["commander", "content_engine", "review_hub", "publish_engine"], "safety": dict(SAFETY)}

    def create_threads_review(self, instruction: str, *, target_account: str, **metadata: Any) -> dict[str, Any]:
        created = self.threads.create_from_commander(instruction, target_account=target_account, **metadata)
        return {**created, "route": ["commander", "content_engine", "review_hub", "publish_engine"], "safety": dict(SAFETY)}

    def dry_run_reviewed(self, queue_id: str) -> dict[str, Any]:
        item = next((row for row in self.queue.mobile_rows() if row.get("queue_id") == queue_id), None)
        if item is None:
            raise KeyError(queue_id)
        if item.get("target_platform") == "threads":
            result = self.threads.dry_run(queue_id)
        elif item.get("target_platform") == "note" and self.note_workspace is not None:
            result = self.note_workspace.accept_mobile_approval(item)
        else:
            raise ValueError("No RC2 DryRun adapter for target platform")
        return {**result, "route": ["review_hub", "publish_engine", item["target_platform"]], "safety": dict(SAFETY)}

    def production(self, queue_id: str) -> dict[str, Any]:
        return {"ok": False, "queue_id": queue_id, "status": "production_blocked", **SAFETY}
