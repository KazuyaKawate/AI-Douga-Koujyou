from __future__ import annotations

from typing import Any
from uuid import uuid4


class WordPressPublisher:
    def publish(self, item: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        content = item.get("content", {})
        seo = content.get("seo", {})
        return {
            "platform": "wordpress",
            "status": "dry_run" if dry_run else "published",
            "external_id": f"wp-{uuid4().hex[:10]}",
            "title": content.get("title", ""),
            "featured_image": content.get("featured_image", ""),
            "tags": content.get("tags", content.get("keywords", [])),
            "categories": content.get("categories", []),
            "seo": seo,
            "dry_run": dry_run,
        }
