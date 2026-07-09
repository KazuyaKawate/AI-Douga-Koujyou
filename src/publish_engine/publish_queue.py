from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class PublishQueue:
    def create_item(self, content: dict[str, Any], platform: str, *, priority: int = 50) -> dict[str, Any]:
        return {
            "publish_id": f"pub-{uuid4().hex[:10]}",
            "content_id": content.get("content_id", ""),
            "platform": platform,
            "status": "draft",
            "priority": int(priority),
            "content": content,
            "attempts": 0,
            "max_attempts": 3,
            "scheduled_for": "",
            "review": {},
            "approval": {},
            "publish_result": {},
            "analytics": {},
            "created_at": now(),
            "updated_at": now(),
        }

    def add(self, state: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
        if self.is_duplicate(state, item):
            return {**item, "status": "duplicate_blocked"}
        state.setdefault("queue", []).insert(0, item)
        return item

    def next_ready(self, state: dict[str, Any]) -> dict[str, Any] | None:
        ready = [item for item in state.get("queue", []) if item.get("status") in {"approved", "scheduled", "retry"}]
        if not ready:
            return None
        return sorted(ready, key=lambda item: (-int(item.get("priority", 0)), item.get("scheduled_for") or ""))[0]

    def update(self, state: dict[str, Any], publish_id: str, **updates: Any) -> dict[str, Any] | None:
        for item in state.setdefault("queue", []):
            if item.get("publish_id") == publish_id:
                item.update(updates)
                item["updated_at"] = now()
                return item
        return None

    @staticmethod
    def is_duplicate(state: dict[str, Any], item: dict[str, Any]) -> bool:
        content_id = item.get("content_id", "")
        platform = item.get("platform", "")
        text = str(item.get("content", {}).get("text") or item.get("content", {}).get("body") or item.get("content", {}).get("title"))
        for existing in state.get("queue", []) + state.get("history", []):
            if existing.get("platform") != platform:
                continue
            existing_text = str(existing.get("content", {}).get("text") or existing.get("content", {}).get("body") or existing.get("content", {}).get("title"))
            if content_id and existing.get("content_id") == content_id:
                return True
            if text and existing_text == text:
                return True
        return False
