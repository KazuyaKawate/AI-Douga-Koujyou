from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from src.content_engine.content_generator import ContentGenerator
from src.mobile_review_hub.queue import CommonPublishQueue, digest
from src.publish_engine.analytics_sync import AnalyticsSync
from src.publish_engine.safety_guard import content_hash
from src.publish_engine.threads_publisher import ThreadsPublisher
from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic

MAX_TEXT_LENGTH = 500
SUPPORTED_MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov"}
SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|authorization)\s*[:=]"
)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def normalize_hashtags(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        clean = "".join(ch for ch in str(value).strip().lstrip("#").replace(" ", "") if ch.isalnum() or ch in {"_", "-"})
        tag = f"#{clean}" if clean else ""
        if tag and tag not in normalized:
            normalized.append(tag)
    return normalized[:10]


def validate_threads_content(content: dict[str, Any], *, root: str | Path = PROJECT_ROOT) -> dict[str, Any]:
    text = str(content.get("text", "")).strip()
    media = str(content.get("media_reference", "")).strip()
    account = str(content.get("target_account", "")).strip()
    errors: list[str] = []
    if not text:
        errors.append("text_required")
    if len(text) > MAX_TEXT_LENGTH:
        errors.append("text_too_long")
    if SECRET_PATTERN.search(text) or SECRET_PATTERN.search(media):
        errors.append("secret_detected")
    if not account:
        errors.append("target_account_required")
    if media:
        parsed = urlparse(media)
        suffix = Path(parsed.path if parsed.scheme else media).suffix.lower()
        if suffix not in SUPPORTED_MEDIA_EXTENSIONS:
            errors.append("unsupported_media_type")
        elif parsed.scheme and parsed.scheme != "https":
            errors.append("media_https_required")
        elif not parsed.scheme:
            path = (Path(root) / media).resolve()
            if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
                errors.append("media_reference_invalid")
    return {
        "ok": not errors,
        "errors": errors,
        "text_length": len(text),
        "max_text_length": MAX_TEXT_LENGTH,
        "hashtags": normalize_hashtags(content.get("hashtags", [])),
        "checked_at": _now(),
    }


class ThreadsPublishingWorkflow:
    """Canonical local-first Threads flow built from existing AIOS components."""

    def __init__(
        self,
        *,
        root: str | Path = PROJECT_ROOT,
        queue: CommonPublishQueue | None = None,
        publisher: ThreadsPublisher | None = None,
        revenue: RevenueEngineDashboard | None = None,
        analytics: AnalyticsSync | None = None,
    ) -> None:
        self.root = Path(root)
        self.path = self.root / "data" / "threads_phase105.json"
        self.queue = queue or CommonPublishQueue(self.root / "data" / "mobile_publish_queue.json")
        self.publisher = publisher or ThreadsPublisher()
        self.revenue = revenue or RevenueEngineDashboard(self.root / "config" / "revenue_engine.json")
        self.analytics = analytics or AnalyticsSync()
        self.generator = ContentGenerator()

    def create_from_commander(
        self,
        instruction: str,
        *,
        target_account: str,
        campaign_id: str = "",
        source_job_id: str = "",
        media_reference: str = "",
        cta: str = "",
        hashtags: list[str] | None = None,
    ) -> dict[str, Any]:
        plan = self.generator.generate(
            {
                "title": instruction,
                "business_category": "Threads",
                "plan_id": campaign_id,
                "task_id": source_job_id,
            },
            dry_run=True,
        )
        tags = normalize_hashtags(hashtags or plan.get("hashtags", []))
        parts = [str(item) for item in plan.get("threads_outline", [])[:4]]
        if cta or plan.get("cta"):
            parts.append(str(cta or plan["cta"]))
        if tags:
            parts.append(" ".join(tags))
        text = "\n".join(parts).strip()
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH].rstrip()
        content = {
            "text": text,
            "hashtags": tags,
            "media_reference": media_reference,
            "target_account": target_account,
            "campaign_id": campaign_id,
            "source_job_id": source_job_id,
            "cta": cta or plan.get("cta", ""),
        }
        validation = validate_threads_content(content, root=self.root)
        if not validation["ok"]:
            raise ValueError("Threads validation failed: " + ", ".join(validation["errors"]))
        source_id = source_job_id or f"threads-{uuid4().hex[:12]}"
        item = self.queue.add(
            target_platform="threads",
            source_id=source_id,
            title=str(plan.get("title", "Threads post")),
            body=text,
            tags=tags,
            hashtags=tags,
            cta=str(content["cta"]),
            media_reference=media_reference,
            target_account=target_account,
            campaign_id=campaign_id,
            source_job_id=source_job_id,
            source_engine="content_engine",
            review_result=validation,
        )
        return {"item": item, "content_plan": plan, "validation": validation, "dry_run": True, "approval_required": True, "execute_allowed": False}

    def dry_run(self, queue_id: str) -> dict[str, Any]:
        state = self.queue.load()
        item = next((row for row in state["items"] if row.get("queue_id") == queue_id), None)
        if item is None:
            raise KeyError(queue_id)
        if item.get("target_platform") != "threads":
            raise ValueError("Threads queue item required")
        approval = item.get("approval", {})
        if item.get("status") != "ready_to_publish" or approval.get("content_hash") != digest(item):
            raise ValueError("MobileReviewHub approval required")
        content = {
            "text": item.get("body", ""),
            "hashtags": item.get("hashtags", item.get("tags", [])),
            "media_reference": item.get("media_reference", ""),
            "target_account": item.get("target_account", ""),
            "campaign_id": item.get("campaign_id", ""),
            "source_job_id": item.get("source_job_id", ""),
            "cta": item.get("cta", ""),
        }
        validation = validate_threads_content(content, root=self.root)
        if not validation["ok"]:
            raise ValueError("Threads validation failed: " + ", ".join(validation["errors"]))
        publisher_item = {
            "content": content,
            "content_version": item["content_version"],
            "approval": {
                "status": "approved",
                "content_hash": content_hash(content),
                "approved_content_version": item["content_version"],
            },
        }
        result = self.publisher.publish(publisher_item, dry_run=True)
        result.update(
            queue_id=queue_id,
            campaign_id=item.get("campaign_id", ""),
            source_job_id=item.get("source_job_id", ""),
            target_account=item.get("target_account", ""),
            published_at=_now(),
            published_url="",
            external_request_sent=False,
            execute_allowed=False,
            approval_required=True,
        )
        callback_state = self._load()
        callback_key = f"{queue_id}:{item['content_hash']}"
        if callback_key not in callback_state["completed"]:
            revenue = self.revenue.record_publish_history({"channel": "threads", **result})
            analytics = self.analytics.sync(publisher_item)
            callback_state["completed"][callback_key] = {
                "revenue": revenue,
                "analytics": analytics,
                "created_at": _now(),
            }
            callback_state["history"].insert(0, {"callback_key": callback_key, "result": result, "created_at": _now()})
            self._save(callback_state)
        callbacks = callback_state["completed"][callback_key]
        return {"result": result, "validation": validation, "callbacks": callbacks, "callback_key": callback_key, "dry_run": True, "execute_allowed": False}

    def production_publish(self, queue_id: str) -> dict[str, Any]:
        return {
            "ok": False,
            "queue_id": queue_id,
            "status": "production_blocked",
            "reason": "execute_allowed=false; Phase 105 requires a later explicit production cutover",
            "dry_run": True,
            "approval_required": True,
            "execute_allowed": False,
            "external_request_sent": False,
        }

    def _load(self) -> dict[str, Any]:
        state = load_json(self.path, default={}) or {}
        state.setdefault("completed", {})
        state.setdefault("history", [])
        return state

    def _save(self, state: dict[str, Any]) -> None:
        state.update(dry_run=True, approval_required=True, execute_allowed=False, updated_at=_now())
        save_json_atomic(self.path, state)
