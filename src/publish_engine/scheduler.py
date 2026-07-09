from __future__ import annotations

from datetime import date, timedelta
from typing import Any


class PublishScheduler:
    def schedule(self, item: dict[str, Any], *, days_from_now: int = 0) -> dict[str, Any]:
        return {
            **item,
            "status": "scheduled",
            "scheduled_for": (date.today() + timedelta(days=max(days_from_now, 0))).isoformat(),
        }
