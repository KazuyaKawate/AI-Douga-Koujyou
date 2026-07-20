from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from src.publish_engine.safety_guard import idempotency_key, now
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


DRAFT = "Draft"
REVIEW = "Review"
APPROVAL_REQUIRED = "ApprovalRequired"
APPROVED = "Approved"
DRY_RUN_QUEUED = "DryRunQueued"
DRY_RUN_SUCCEEDED = "DryRunSucceeded"
DRY_RUN_FAILED = "DryRunFailed"
PUBLISHED_RESERVED = "PublishedReserved"
PUBLISHED = "Published"

ALLOWED = {
    DRAFT: {REVIEW},
    REVIEW: {APPROVAL_REQUIRED},
    APPROVAL_REQUIRED: {APPROVED},
    APPROVED: {DRY_RUN_QUEUED},
    DRY_RUN_QUEUED: {DRY_RUN_SUCCEEDED, DRY_RUN_FAILED},
    DRY_RUN_FAILED: set(),
    DRY_RUN_SUCCEEDED: {PUBLISHED_RESERVED},
    PUBLISHED_RESERVED: set(),
    PUBLISHED: set(),
}


class QueueTransitionError(RuntimeError):
    pass


class SafePublishQueue:
    def __init__(self, path: str | Path = PROJECT_ROOT / "config" / "monetization_publish_queue.json") -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        state = load_json(self.path, default={}) or {}
        state.setdefault("items", [])
        state.setdefault("idempotency_results", {})
        return state

    def create(self, *, channel: str, content_id: str, content_version: int, digest: str, scheduled_at: str = "") -> dict[str, Any]:
        state = self.load()
        key = idempotency_key(channel, content_id, content_version, digest)
        existing = next((row for row in state["items"] if row.get("idempotency_key") == key), None)
        if existing:
            return existing
        row = {
            "queue_id": f"pq-{uuid4().hex[:12]}",
            "channel": channel,
            "content_id": content_id,
            "content_version": content_version,
            "scheduled_at": scheduled_at,
            "status": DRAFT,
            "approval_id": "",
            "idempotency_key": key,
            "created_at": now(),
            "updated_at": now(),
            "error_summary": "",
        }
        state["items"].insert(0, row)
        self.save(state)
        return row

    def transition(self, queue_id: str, target: str, *, approval_id: str = "", error_summary: str = "") -> dict[str, Any]:
        if target == PUBLISHED:
            raise QueueTransitionError("Published transition is disabled")
        state = self.load()
        row = next((item for item in state["items"] if item.get("queue_id") == queue_id), None)
        if row is None:
            raise QueueTransitionError("queue item not found")
        if target not in ALLOWED.get(row["status"], set()):
            raise QueueTransitionError(f"invalid transition: {row['status']} -> {target}")
        row["status"] = target
        row["approval_id"] = approval_id or row.get("approval_id", "")
        row["error_summary"] = error_summary[:300]
        row["updated_at"] = now()
        self.save(state)
        return row

    def result_for(self, key: str) -> dict[str, Any] | None:
        return self.load().get("idempotency_results", {}).get(key)

    def save_result(self, key: str, result: dict[str, Any]) -> None:
        state = self.load()
        state["idempotency_results"][key] = result
        self.save(state)

    def save(self, state: dict[str, Any]) -> None:
        state["local_first"] = True
        state["updated_at"] = now()
        save_json_atomic(self.path, state)

