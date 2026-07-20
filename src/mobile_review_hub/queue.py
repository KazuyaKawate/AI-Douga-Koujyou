from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import uuid4

from src.publish_engine.safety_guard import mask_secrets
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic

STATUSES = {"draft", "review_required", "changes_requested", "approved", "ready_to_publish", "published_manual", "failed", "rejected", "cancelled"}
TARGETS = {"note", "threads", "website", "gmail", "google_docs", "google_drive"}
OPEN_URLS = {"note": "https://note.com/notes/new", "threads": "https://www.threads.com/", "gmail": "https://mail.google.com/mail/u/0/#drafts", "google_docs": "https://docs.google.com/", "google_drive": "https://drive.google.com/"}
EDITABLE = {"title", "body", "tags", "hashtags", "cta", "price", "publication_type", "planned_publish_at", "notes", "image_path", "media_reference", "target_account", "campaign_id"}
SECRET_TEXT = re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization|cookie)\s*[:=]\s*[^\s,;]+")

def now() -> str: return datetime.now().astimezone().isoformat(timespec="seconds")

def digest(item: dict[str, Any]) -> str:
    content = {key: item.get(key) for key in ("target_platform", "title", "body", "tags", "hashtags", "cta", "price", "publication_type", "planned_publish_at", "recipient", "image_path", "media_reference", "target_account", "campaign_id", "source_job_id")}
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def safe(value: Any) -> Any:
    masked = mask_secrets(value)
    if isinstance(masked, dict): return {k: safe(v) for k, v in masked.items()}
    if isinstance(masked, list): return [safe(v) for v in masked]
    if isinstance(masked, str): return SECRET_TEXT.sub(lambda m: m.group(1) + "=***REDACTED***", masked)
    return masked

def validate_url(platform: str, value: str) -> tuple[str, str]:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname: raise ValueError("HTTPSの公開URLが必要です")
    host = parsed.hostname.lower()
    allowed = {"note": ("note.com",), "threads": ("threads.net", "threads.com"), "gmail": ("mail.google.com",), "google_docs": ("docs.google.com",), "google_drive": ("drive.google.com",)}
    if platform in allowed and not any(host == suffix or host.endswith("." + suffix) for suffix in allowed[platform]): raise ValueError("投稿先ドメインと一致しません")
    match = re.search(r"/(?:n|post)/([A-Za-z0-9_-]+)", parsed.path)
    return value.strip(), match.group(1) if match else ""

class CommonPublishQueue:
    def __init__(self, path: str | Path = PROJECT_ROOT / "data" / "mobile_publish_queue.json", *, business: Any = None, revenue: Any = None) -> None:
        self.path = Path(path); self.business = business; self.revenue = revenue

    def load(self) -> dict[str, Any]:
        state = load_json(self.path, default={}) or {}; state.setdefault("items", []); state.setdefault("history", []); state.setdefault("idempotency", {})
        state.update(local_first=True, dry_run=True, review_required=True, production_actions_enabled=False, execute_allowed=False)
        return state

    def add(self, *, target_platform: str, source_id: str, title: str = "", body: str = "", tags: list[str] | None = None, hashtags: list[str] | None = None, cta: str = "", price: int = 0, publication_type: str = "draft", planned_publish_at: str = "", image_path: str = "", media_reference: str = "", recipient: str = "", target_account: str = "", campaign_id: str = "", source_job_id: str = "", source_engine: str = "", review_result: dict[str, Any] | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
        platform = target_platform.lower()
        if platform not in TARGETS: platform = "website"
        state = self.load(); key = f"{platform}:{source_id}"
        existing_id = state["idempotency"].get(key)
        if existing_id: return next(row for row in state["items"] if row["queue_id"] == existing_id)
        row = {"queue_id": f"mph-{uuid4().hex[:12]}", "source_id": source_id, "target_platform": platform, "title": title.strip(), "body": body.strip(), "tags": list(tags or []), "hashtags": list(hashtags or tags or []), "cta": cta.strip(), "price": max(0, int(price)), "publication_type": publication_type, "planned_publish_at": planned_publish_at, "image_path": image_path, "media_reference": media_reference, "recipient": recipient, "target_account": target_account, "campaign_id": campaign_id, "source_job_id": source_job_id, "notes": "", "review_result": review_result or {}, "warnings": warnings or [], "status": "review_required", "approval": {}, "content_version": 1, "content_hash": "", "created_at": now(), "updated_at": now(), "source_engine": source_engine or platform, "dry_run": True, "approval_required": True, "review_required": True, "production_actions_enabled": False, "execute_allowed": False}
        row["content_hash"] = digest(row); safe_row = safe(row); safe_row["content_hash"] = digest(safe_row); state["items"].insert(0, safe_row); state["idempotency"][key] = row["queue_id"]; self._event(state, safe_row, "queued"); self._save(state); return safe_row

    def mobile_rows(self) -> list[dict[str, Any]]:
        return [safe(row) for row in self.load()["items"] if row.get("status") not in {"cancelled"}]

    def update(self, queue_id: str, *, operator: str, **changes: Any) -> dict[str, Any]:
        state, row = self._find(queue_id)
        before = {k: row.get(k) for k in EDITABLE}
        for key, value in changes.items():
            if key in EDITABLE: row[key] = list(value) if key == "tags" and isinstance(value, list) else value
        row.update(content_version=int(row.get("content_version", 1)) + 1, approval={}, status="review_required", review_required=True, updated_at=now())
        row["content_hash"] = digest(row); self._event(state, row, "content_updated_approval_invalidated", {"operator": operator, "before": before}); self._save(state); return row

    def request_changes(self, queue_id: str, *, operator: str, reason: str) -> dict[str, Any]:
        state, row = self._find(queue_id); row.update(status="changes_requested", approval={}, updated_at=now(), notes=reason)
        self._event(state, row, "changes_requested", {"operator": operator, "reason": reason}); self._save(state); return row

    def approve(self, queue_id: str, *, approver: str, device_type: str, review_result: str, confirmation_token: str) -> dict[str, Any]:
        if not confirmation_token: raise ValueError("誤操作防止確認が必要です")
        state, row = self._find(queue_id)
        if row["status"] not in {"review_required", "changes_requested"}: raise ValueError("承認可能な状態ではありません")
        current = digest(row)
        if current != row.get("content_hash"): raise ValueError("content_hash不一致")
        row["approval"] = {"approval_id": f"map-{uuid4().hex[:12]}", "approver": approver, "approved_at": now(), "content_hash": current, "content_version": row["content_version"], "target_platform": row["target_platform"], "device_type": device_type, "review_result": review_result}
        row.update(status="ready_to_publish", updated_at=now()); self._event(state, row, "human_approved"); self._save(state); return row

    def open_target(self, queue_id: str) -> str:
        _, row = self._find(queue_id)
        if row.get("status") != "ready_to_publish" or row.get("approval", {}).get("content_hash") != digest(row): raise ValueError("承認済み内容だけ投稿先を開けます")
        return OPEN_URLS.get(row["target_platform"], "") or str(row.get("preview_url", ""))

    def record_published(self, queue_id: str, *, url: str, published_at: str, confirmed_by: str, external_id: str = "", notes: str = "", confirmation_token: str = "", canonical_recorder: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None) -> dict[str, Any]:
        if not confirmation_token: raise ValueError("公開完了確認が必要です")
        state, row = self._find(queue_id)
        if row.get("status") != "ready_to_publish" or row.get("approval", {}).get("content_hash") != digest(row): raise ValueError("承認済み内容と一致しません")
        safe_url, derived = validate_url(row["target_platform"], url)
        if any(x.get("published_url") == safe_url for x in state["items"]): raise ValueError("公開URLは登録済みです")
        record = {"published_url": safe_url, "published_at": published_at, "confirmed_by": confirmed_by, "external_id": external_id or derived, "publication_notes": notes, "status": "published_manual", "recorded_at": now(), "external_request_sent": False}
        canonical_result = canonical_recorder(row, record) if canonical_recorder else None
        row.update(record, updated_at=now(), kpi={"pv": None, "ctr": None, "sales": 0, "purchases": None, "likes": None, "comments": None})
        self._event(state, row, "published_manual_recorded", record); self._save(state)
        if canonical_result is None:
            if self.business: self.business.record_daily_kpi(revenue=0, articles=1 if row["target_platform"] == "note" else 0, note_articles=1 if row["target_platform"] == "note" else 0, posts=1, pv=0, ctr=0, notes=f"mobile hub: {queue_id}")
            if self.revenue: self.revenue.record_publish_history({"queue_id": queue_id, "channel": row["target_platform"], **record, "dry_run": True})
        return row

    def cancel(self, queue_id: str, *, operator: str) -> dict[str, Any]:
        state, row = self._find(queue_id); row.update(status="cancelled", updated_at=now()); self._event(state, row, "cancelled", {"operator": operator}); self._save(state); return row

    def reject(self, queue_id: str, *, operator: str, reason: str = "") -> dict[str, Any]:
        state, row = self._find(queue_id); row.update(status="rejected", approval={}, notes=reason, updated_at=now())
        self._event(state, row, "rejected", {"operator": operator, "reason": reason}); self._save(state); return row

    def production_publish(self, queue_id: str) -> dict[str, Any]:
        return {"ok": False, "queue_id": queue_id, "status": "production_blocked", "external_request_sent": False, "dry_run": True, "production_actions_enabled": False, "execute_allowed": False}

    def _find(self, queue_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        state = self.load(); row = next((x for x in state["items"] if x.get("queue_id") == queue_id), None)
        if not row: raise KeyError(queue_id)
        return state, row
    def _event(self, state: dict[str, Any], row: dict[str, Any], event: str, details: dict[str, Any] | None = None) -> None:
        state["history"].insert(0, safe({"audit_id": f"mha-{uuid4().hex[:10]}", "queue_id": row["queue_id"], "event": event, "status": row["status"], "content_hash": row["content_hash"], "at": now(), "details": details or {}, "dry_run": True}))
    def _save(self, state: dict[str, Any]) -> None:
        state.update(updated_at=now(), local_first=True, dry_run=True, approval_required=True, review_required=True, production_actions_enabled=False, execute_allowed=False); save_json_atomic(self.path, state)
