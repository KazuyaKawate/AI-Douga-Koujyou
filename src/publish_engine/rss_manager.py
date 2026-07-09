from __future__ import annotations

from typing import Any
from uuid import uuid4


class RSSManager:
    def publish(self, item: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        content = item.get("content", {})
        return {
            "platform": "rss",
            "status": "dry_run" if dry_run else "published",
            "external_id": f"rss-{uuid4().hex[:10]}",
            "title": content.get("title", ""),
            "link": content.get("canonical", ""),
            "dry_run": dry_run,
        }
