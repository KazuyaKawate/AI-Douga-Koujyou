from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


class RollbackManager:
    def create_plan(self, item: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            "rollback_id": f"rb-{uuid4().hex[:10]}",
            "publish_id": item.get("publish_id", ""),
            "platform": item.get("platform", ""),
            "reason": reason,
            "actions": ["unpublish_or_revert_external_post", "restore_previous_content", "record_failure_learning"],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
