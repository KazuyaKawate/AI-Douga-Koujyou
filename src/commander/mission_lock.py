from __future__ import annotations

from typing import Any


ALLOWED_MISSION = ("commander", "development", "note", "threads", "website")
CORE_ALLOWED = {"commander", "note", "threads", "website"}


class MissionLock:
    def evaluate(self, plan: dict[str, Any]) -> dict[str, Any]:
        task = plan.get("business_task", {})
        categories = set(task.get("categories", []))
        disallowed = categories - set(ALLOWED_MISSION)
        allowed = bool(categories & CORE_ALLOWED) or ("development" in categories and not disallowed)
        roi = float(task.get("roi", 0) or 0)
        low_roi = roi < 1000
        blocked = (not allowed) or low_roi
        return {
            "ok": not blocked,
            "blocked": blocked,
            "allowed_mission": list(ALLOWED_MISSION),
            "categories": sorted(categories),
            "roi": roi,
            "reason": "" if not blocked else "Mission Lock: AIOS自己開発/note/Threads/公式サイト以外、またはROI低案件のためreject。",
        }
