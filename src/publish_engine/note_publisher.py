from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.publish_engine.safety_guard import PublishSafetyGuard


class NotePublisher:
    def publish(self, item: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        if dry_run is not True:
            raise ValueError("note live publishing is disabled; dry_run=True is required")
        content = item.get("content", {})
        PublishSafetyGuard().enforce(
            channel="note", dry_run=True, production_actions_enabled=False,
            review_required=True, approval=item.get("approval"), content=content,
            content_version=int(item.get("content_version", 1)),
        )
        return {
            "platform": "note",
            "status": "dry_run",
            "external_id": f"note-{uuid4().hex[:10]}",
            "title": content.get("title", ""),
            "body_length": len(str(content.get("body", ""))),
            "tags": content.get("tags", content.get("keywords", [])),
            "categories": content.get("categories", []),
            "scheduled": bool(item.get("scheduled_for")),
            "dry_run": True,
            "external_request_sent": False,
        }
