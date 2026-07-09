from __future__ import annotations

from typing import Any
from uuid import uuid4


class NotePublisher:
    def publish(self, item: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        content = item.get("content", {})
        return {
            "platform": "note",
            "status": "dry_run" if dry_run else "published",
            "external_id": f"note-{uuid4().hex[:10]}",
            "title": content.get("title", ""),
            "body_length": len(str(content.get("body", ""))),
            "tags": content.get("tags", content.get("keywords", [])),
            "categories": content.get("categories", []),
            "scheduled": bool(item.get("scheduled_for")),
            "dry_run": dry_run,
        }
