from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


class PublishLogger:
    def entry(self, item: dict[str, Any], event: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "log_id": f"plog-{uuid4().hex[:10]}",
            "publish_id": item.get("publish_id", ""),
            "platform": item.get("platform", ""),
            "event": event,
            "payload": payload or {},
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
