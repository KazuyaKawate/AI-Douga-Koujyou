from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


class RetryManager:
    def queue_retry(self, item: dict[str, Any], error: str) -> dict[str, Any]:
        attempts = int(item.get("attempts", 0)) + 1
        return {
            "retry_id": f"retry-{uuid4().hex[:10]}",
            "publish_id": item.get("publish_id", ""),
            "status": "retry" if attempts < int(item.get("max_attempts", 3)) else "failed",
            "attempts": attempts,
            "error": error,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
