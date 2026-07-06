"""approval_queue — Approval queue manager for Creator Factory OS.

Stores action approvals and generated content reviews in config/approval_queue.json.
Never executes actions or publishes externally.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.approval.approval_models import CONTENT_STATUSES, CONTENT_TYPES, STATUSES, is_pending, make_item
from src.approval.risk_analyzer import analyze_content_risk
from src.utils.json_store import save_json_atomic

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "approval_queue.json"
OUTPUT_ROOT = ROOT / "output"
MAX_HISTORY = 100


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_store() -> dict[str, Any]:
    return {
        "meta": {"version": "5.2-phase7", "created_at": _now()},
        "pending": [],
        "history": [],
        "content_reviews": [],
        "content_audit": [],
    }


def load_queue() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            defaults = _default_store()
            for key, value in defaults.items():
                data.setdefault(key, value)
            return data
        except Exception:
            pass
    return _default_store()


def save_queue(data: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data.setdefault("meta", {})
    data["meta"]["updated_at"] = _now()
    save_json_atomic(CONFIG_PATH, data)


def get_pending() -> list[dict]:
    data = load_queue()
    return [item for item in data.get("pending", []) if item.get("status") == "pending"]


def get_all_pending_raw() -> list[dict]:
    return load_queue().get("pending", [])


def get_history(limit: int = 50) -> list[dict]:
    return load_queue().get("history", [])[:limit]


def add_item(
    title: str,
    source: str,
    command_summary: str,
    expected_impact: str,
    estimated_risk: str = "low",
    affected_files: list[str] | None = None,
    related_id: str = "",
    notes: str = "",
) -> dict:
    """Add a new pending action item. Returns the created item."""
    item = make_item(
        title=title,
        source=source,
        command_summary=command_summary,
        expected_impact=expected_impact,
        estimated_risk=estimated_risk,
        affected_files=affected_files,
        related_id=related_id,
        notes=notes,
    )
    data = load_queue()
    data.setdefault("pending", []).insert(0, item)
    save_queue(data)
    return item


def _update_item_status(approval_id: str, status: str, notes: str = "") -> dict | None:
    """Internal: move an action item from pending to history with new status."""
    data = load_queue()
    pending = data.get("pending", [])
    target = next((i for i in pending if i.get("approval_id") == approval_id), None)
    if not target:
        return None

    target["status"] = status
    target["reviewed_at"] = _now()
    if notes:
        target["notes"] = notes

    data["pending"] = [i for i in pending if i.get("approval_id") != approval_id]
    history = data.setdefault("history", [])
    history.insert(0, target)
    if len(history) > MAX_HISTORY:
        data["history"] = history[:MAX_HISTORY]

    save_queue(data)
    return target


def approve_item(approval_id: str, notes: str = "") -> dict | None:
    return _update_item_status(approval_id, "approved", notes)


def reject_item(approval_id: str, notes: str = "") -> dict | None:
    return _update_item_status(approval_id, "rejected", notes)


def expire_item(approval_id: str) -> dict | None:
    return _update_item_status(approval_id, "expired")


def delete_pending(approval_id: str) -> bool:
    data = load_queue()
    before = len(data.get("pending", []))
    data["pending"] = [i for i in data.get("pending", []) if i.get("approval_id") != approval_id]
    if len(data["pending"]) < before:
        save_queue(data)
        return True
    return False


def create_content_review_item(
    title: str,
    content: str,
    content_type: str,
    *,
    source_job_id: str = "",
    reviewer_notes: str = "",
) -> dict[str, Any]:
    if content_type not in CONTENT_TYPES:
        content_type = "business_report"
    item = {
        "id": f"rev_{uuid.uuid4().hex[:10]}",
        "title": title,
        "content": content,
        "content_type": content_type,
        "source_job_id": source_job_id,
        "generated_at": _now(),
        "status": "pending_review",
        "reviewer_notes": reviewer_notes,
        "risk_flags": analyze_content_risk(content, content_type),
        "approval_history": [
            {"action": "created", "status": "pending_review", "notes": "", "created_at": _now()}
        ],
        "approved_at": "",
        "rejected_at": "",
        "revised_at": "",
    }
    data = load_queue()
    data.setdefault("content_reviews", []).insert(0, item)
    _audit_content(data, item, "created", "pending_review", "")
    save_queue(data)
    return item


def get_content_reviews(status: str | None = None) -> list[dict[str, Any]]:
    rows = load_queue().get("content_reviews", [])
    if status is None:
        return rows
    return [row for row in rows if row.get("status") == status]


def approve_content_item(item_id: str, notes: str = "") -> dict[str, Any] | None:
    return _update_content_status(item_id, "approved", notes, timestamp_field="approved_at")


def reject_content_item(item_id: str, notes: str = "") -> dict[str, Any] | None:
    return _update_content_status(item_id, "rejected", notes, timestamp_field="rejected_at")


def request_content_revision(item_id: str, notes: str = "") -> dict[str, Any] | None:
    return _update_content_status(item_id, "revision_requested", notes, timestamp_field="revised_at")


def mark_content_publish_ready(item_id: str, notes: str = "") -> dict[str, Any] | None:
    return _update_content_status(item_id, "publish_ready", notes)


def _update_content_status(
    item_id: str,
    status: str,
    notes: str = "",
    *,
    timestamp_field: str = "",
) -> dict[str, Any] | None:
    if status not in CONTENT_STATUSES:
        return None
    data = load_queue()
    item = next((row for row in data.get("content_reviews", []) if row.get("id") == item_id), None)
    if item is None:
        return None
    item["status"] = status
    if notes:
        item["reviewer_notes"] = notes
    if timestamp_field:
        item[timestamp_field] = _now()
    item.setdefault("approval_history", []).insert(0, {
        "action": status,
        "status": status,
        "notes": notes,
        "created_at": _now(),
    })
    _audit_content(data, item, status, status, notes)
    save_queue(data)
    return item


def export_content_item(item_id: str, target_status: str | None = None) -> dict[str, Path] | None:
    data = load_queue()
    item = next((row for row in data.get("content_reviews", []) if row.get("id") == item_id), None)
    if item is None:
        return None
    status = target_status or item.get("status", "pending_review")
    if status not in {"approved", "publish_ready", "rejected"}:
        status = item.get("status", "pending_review")
    folder_name = {
        "approved": "approved",
        "publish_ready": "publish_ready",
        "rejected": "rejected",
    }.get(status, "approved")
    out_dir = OUTPUT_ROOT / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(f"{item.get('content_type', 'content')}_{item.get('id', '')}")
    md_path = out_dir / f"{safe_name}.md"
    json_path = out_dir / f"{safe_name}.json"
    md_path.write_text(_content_markdown(item), encoding="utf-8")
    save_json_atomic(json_path, item)
    _audit_content(data, item, f"exported_{folder_name}", item.get("status", ""), str(md_path))
    save_queue(data)
    return {"markdown": md_path, "json": json_path}


def content_review_summary() -> dict[str, Any]:
    rows = load_queue().get("content_reviews", [])
    today = date.today().isoformat()
    approved_today = sum(1 for row in rows if str(row.get("approved_at", "")).startswith(today))
    rejected_today = sum(1 for row in rows if str(row.get("rejected_at", "")).startswith(today))
    risk_warnings = sum(len(row.get("risk_flags", [])) for row in rows if row.get("status") == "pending_review")
    return {
        "pending_reviews": sum(1 for row in rows if row.get("status") == "pending_review"),
        "approved_today": approved_today,
        "rejected_today": rejected_today,
        "revision_requested": sum(1 for row in rows if row.get("status") == "revision_requested"),
        "publish_ready": sum(1 for row in rows if row.get("status") == "publish_ready"),
        "risk_warnings": risk_warnings,
        "approved_total": sum(1 for row in rows if row.get("status") == "approved"),
        "rejected_total": sum(1 for row in rows if row.get("status") == "rejected"),
    }


def _audit_content(data: dict[str, Any], item: dict[str, Any], action: str, status: str, notes: str) -> None:
    data.setdefault("content_audit", []).insert(0, {
        "item_id": item.get("id", ""),
        "title": item.get("title", ""),
        "action": action,
        "status": status,
        "notes": notes,
        "created_at": _now(),
    })
    data["content_audit"] = data["content_audit"][:300]


def _content_markdown(item: dict[str, Any]) -> str:
    flags = item.get("risk_flags", [])
    risk_text = "\n".join(f"- {flag.get('severity')}: {flag.get('label')}" for flag in flags) or "- none"
    return (
        f"# {item.get('title', '')}\n\n"
        f"- ID: {item.get('id', '')}\n"
        f"- Type: {item.get('content_type', '')}\n"
        f"- Status: {item.get('status', '')}\n"
        f"- Source Job: {item.get('source_job_id', '')}\n\n"
        "## Risk Flags\n\n"
        f"{risk_text}\n\n"
        "## Reviewer Notes\n\n"
        f"{item.get('reviewer_notes', '')}\n\n"
        "## Content\n\n"
        f"{item.get('content', '')}\n"
    )


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value).strip("_") or "content"


def get_summary() -> dict:
    data = load_queue()
    pending = [i for i in data.get("pending", []) if i.get("status") == "pending"]
    history = data.get("history", [])
    approved = [i for i in history if i.get("status") == "approved"]
    rejected = [i for i in history if i.get("status") == "rejected"]
    high_risk = [i for i in pending if i.get("estimated_risk") == "high"]
    content_summary = content_review_summary()
    return {
        "pending_count": len(pending),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "high_risk_count": len(high_risk),
        "total_reviewed": len(history),
        **content_summary,
    }
