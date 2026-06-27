"""approval_models — Data models and constants for Approval Center."""
from __future__ import annotations
import uuid
from datetime import datetime

STATUSES = ["pending", "approved", "rejected", "expired"]
RISK_LEVELS = ["none", "low", "medium", "high"]
SOURCES = ["aiceo", "automation", "devstudio", "manual"]

STATUS_ICONS = {
    "pending":  "⏳",
    "approved": "✅",
    "rejected": "❌",
    "expired":  "🕒",
}

RISK_ICONS = {
    "none":   "🟢",
    "low":    "🟡",
    "medium": "🟠",
    "high":   "🔴",
}

SOURCE_LABELS = {
    "aiceo":      "AI CEO Core",
    "automation": "自動化工場",
    "devstudio":  "Development Studio",
    "manual":     "手動リクエスト",
}


def make_item(
    title: str,
    source: str,
    command_summary: str,
    expected_impact: str,
    estimated_risk: str = "low",
    affected_files: list[str] | None = None,
    related_id: str = "",
    notes: str = "",
) -> dict:
    """Create a new approval item dict."""
    if source not in SOURCES:
        source = "manual"
    if estimated_risk not in RISK_LEVELS:
        estimated_risk = "low"
    return {
        "approval_id":    f"apv_{uuid.uuid4().hex[:8]}",
        "title":          title,
        "source":         source,
        "command_summary":  command_summary,
        "expected_impact":  expected_impact,
        "estimated_risk":   estimated_risk,
        "affected_files":   affected_files or [],
        "related_id":       related_id,
        "notes":            notes,
        "status":           "pending",
        "created_at":       datetime.now().isoformat(timespec="seconds"),
        "reviewed_at":      "",
        "reviewed_by":      "",
    }


def is_pending(item: dict) -> bool:
    return item.get("status") == "pending"


def is_reviewed(item: dict) -> bool:
    return item.get("status") in ("approved", "rejected", "expired")
