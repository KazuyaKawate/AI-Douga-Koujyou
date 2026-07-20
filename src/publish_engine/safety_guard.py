from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


SECRET_KEYS = re.compile(r"(api[_-]?key|access[_-]?token|refresh[_-]?token|oauth|cookie|client[_-]?secret|authorization|password)", re.I)
SECRET_VALUES = re.compile(r"(Bearer\s+[A-Za-z0-9._~+/=-]+|AIza[0-9A-Za-z_-]{20,}|EA[A-Za-z0-9]{20,})", re.I)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def content_hash(content: dict[str, Any]) -> str:
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def idempotency_key(channel: str, content_id: str, version: int, digest: str) -> str:
    raw = f"{channel}:{content_id}:{version}:{digest}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def mask_secrets(value: Any, *, key: str = "") -> Any:
    if SECRET_KEYS.search(key):
        return "***REDACTED***"
    if isinstance(value, dict):
        return {str(k): mask_secrets(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [mask_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [mask_secrets(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUES.sub("***REDACTED***", value)
    return value


class PublishSafetyError(RuntimeError):
    pass


class PublishSafetyGuard:
    """Shared runtime guard for every note/Threads publish path."""

    def enforce(
        self,
        *,
        channel: str,
        dry_run: bool,
        production_actions_enabled: bool,
        review_required: bool,
        approval: dict[str, Any] | None,
        content: dict[str, Any],
        content_version: int,
    ) -> dict[str, Any]:
        if channel not in {"note", "threads"}:
            raise PublishSafetyError("unsupported_channel")
        if dry_run is not True:
            raise PublishSafetyError("dry_run_false_rejected")
        if production_actions_enabled is not False:
            raise PublishSafetyError("production_actions_must_be_false")
        if review_required is not True:
            raise PublishSafetyError("review_required_must_be_true")
        if not approval or approval.get("status") != "approved":
            raise PublishSafetyError("human_approval_required")
        digest = content_hash(content)
        if approval.get("content_hash") != digest or int(approval.get("approved_content_version", 0)) != int(content_version):
            raise PublishSafetyError("approval_invalidated_by_content_change")
        return {
            "ok": True,
            "channel": channel,
            "dry_run": True,
            "review_required": True,
            "production_actions_enabled": False,
            "content_hash": digest,
        }


class LocalAuditLog:
    def __init__(self, path: str | Path = PROJECT_ROOT / "config" / "monetization_audit.json") -> None:
        self.path = Path(path)

    def append(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        state = load_json(self.path, default={}) or {}
        state.setdefault("events", [])
        row = {"event": event, "created_at": now(), **mask_secrets(payload)}
        state["events"].insert(0, row)
        state["events"] = state["events"][:500]
        state["local_first"] = True
        state["updated_at"] = now()
        save_json_atomic(self.path, state)
        return row

