from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import uuid4


class ContentScheduler:
    def schedule(self, contents: list[dict[str, Any]], *, cadence: str = "daily") -> list[dict[str, Any]]:
        delta = {"daily": 1, "weekly": 7, "monthly": 30}.get(cadence, 1)
        rows = []
        for index, content in enumerate(contents):
            rows.append(
                {
                    "schedule_id": f"sch-{uuid4().hex[:10]}",
                    "content_id": content.get("content_id", ""),
                    "title": content.get("title") or content.get("topic") or content.get("type"),
                    "type": content.get("type", ""),
                    "priority": max(1, 100 - index * 10),
                    "cadence": cadence,
                    "scheduled_for": (date.today() + timedelta(days=index * delta)).isoformat(),
                    "status": "scheduled",
                }
            )
        return rows
