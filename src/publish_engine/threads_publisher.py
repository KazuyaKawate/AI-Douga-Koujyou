from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.api_connectors.manager import APIConnectorManager
from src.publish_engine.safety_guard import PublishSafetyGuard


class ThreadsPublisher:
    """Publish Engine adapter for Meta official Threads API only."""

    def __init__(self, manager: APIConnectorManager | None = None) -> None:
        self.manager = manager or APIConnectorManager()

    def publish(self, item: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        if dry_run is not True:
            raise ValueError("Threads live publishing is disabled; dry_run=True is required")
        content = item.get("content", {})
        PublishSafetyGuard().enforce(
            channel="threads", dry_run=True, production_actions_enabled=False,
            review_required=True, approval=item.get("approval"), content=content,
            content_version=int(item.get("content_version", 1)),
        )
        text = str(content.get("text") or content.get("title", ""))[:500]
        base = {
            "platform": "threads",
            "external_id": f"thr-{uuid4().hex[:10]}",
            "text": text,
            "image_attached": bool(content.get("image") or content.get("image_prompt")),
            "thread_post": bool(content.get("thread") or content.get("reply_chain")),
            "dry_run": dry_run,
            "api": "meta_official_threads_api",
        }
        if not text.strip():
            return {**base, "status": "failed", "message": "Threads text is empty."}
        create = self.manager.create_post("threads", text, dry_run=True)
        if not create.get("ok"):
            return {**base, "status": "failed", "message": _error_message(create), "create": create}
        creation_id = str(create.get("body", {}).get("id", ""))
        published = self.manager.publish_post("threads", creation_id, dry_run=True)
        status = "dry_run" if published.get("ok") else "failed"
        external_id = str(published.get("body", {}).get("id") or creation_id or base["external_id"])
        return {
            **base,
            "status": status,
            "external_id": external_id,
            "create": create,
            "publish": published,
            "message": "Threads post completed via Meta official API." if status == "published" else _error_message(published),
            "external_request_sent": False,
        }


def _error_message(result: dict[str, Any]) -> str:
    body = result.get("body", {})
    if isinstance(body, dict):
        err = body.get("error", "")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("error") or "")
        return str(err or result.get("status", ""))
    return str(result.get("error") or result.get("status", ""))
