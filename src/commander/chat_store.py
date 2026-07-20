from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic

CHAT_ROOT = PROJECT_ROOT / "data" / "commander_chat"
TERMINAL = {"completed", "failed", "dry_run_completed", "rejected", "deferred"}
PROGRESS_STAGES = (
    ("waiting", "待機"),
    ("planning", "計画"),
    ("running", "実行"),
    ("dry_run_completed", "DryRun完了"),
    ("approved", "承認待ち"),
    ("completed", "完了"),
)
PROGRESS_VALUES = {
    "waiting": 10, "retry_queued": 10, "planning": 25, "running": 45,
    "dry_run_completed": 65, "approved": 85, "completed": 100, "failed": 100,
}
STATUS_TEXT = {
    "waiting": "受付済み", "retry_queued": "受付済み", "planning": "計画",
    "running": "実行中", "completed": "完了", "dry_run_completed": "人間の承認待ち",
    "approved": "人間の承認待ち", "failed": "失敗", "rejected": "差し戻し",
}
SECRET_KEYS = re.compile(r"(api.?key|token|secret|password|authorization|oauth|credential|cookie)", re.I)
SECRET_TEXT = re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*([^\s,;]+)")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def mask_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "***MASKED***" if SECRET_KEYS.search(str(key)) else mask_secrets(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_secrets(item) for item in value]
    if isinstance(value, str):
        return SECRET_TEXT.sub(lambda match: f"{match.group(1)}=***MASKED***", value)
    return value


def safe_chat_context(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a masked, presentation-only Commander Chat payload."""
    return {
        **mask_secrets(payload or {}),
        "local_first": True,
        "dry_run": True,
        "approval_required": True,
        "review_required": True,
        "execute_allowed": False,
        "production_actions_enabled": False,
        "external_request_sent": False,
    }


def stream_text_chunks(text: str, *, chunk_size: int = 18) -> list[str]:
    """Split an already available response for UI streaming without external I/O."""
    safe_text = str(mask_secrets(text))
    size = max(1, int(chunk_size))
    return [safe_text[index:index + size] for index in range(0, len(safe_text), size)] or [""]


def result_text(result: Any) -> str:
    if isinstance(result, str):
        return str(mask_secrets(result))
    if not isinstance(result, dict):
        return "処理結果を取得しました。"
    for key in ("summary", "message", "output", "error"):
        if result.get(key):
            value = result[key]
            return str(mask_secrets(value)) if isinstance(value, str) else json.dumps(mask_secrets(value), ensure_ascii=False)
    nested = result.get("result")
    if nested is not None:
        return result_text(nested)
    status = STATUS_TEXT.get(str(result.get("status", "")), str(result.get("status", "完了")))
    return f"処理状態: {status}"


def status_text(status: str) -> str:
    return STATUS_TEXT.get(status, status or "不明")


def progress_label(status: str) -> str:
    for key, label in PROGRESS_STAGES:
        if status == key or (status == "retry_queued" and key == "waiting"):
            return label
    if status == "failed":
        return "失敗"
    return status_text(status)


def progress_value(status: str) -> int:
    return PROGRESS_VALUES.get(status, 5)


def active_stage_index(status: str) -> int:
    mapping = {"waiting": 0, "retry_queued": 0, "planning": 1, "running": 2, "dry_run_completed": 3, "approved": 4, "completed": 5, "failed": 5}
    return mapping.get(status, 0)


class CommanderChatStore:
    def __init__(self, root: str | Path = CHAT_ROOT) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, title: str = "新しい会話") -> dict[str, Any]:
        conversation = {"conversation_id": f"chat-{uuid4().hex[:10]}", "title": title[:60], "created_at": _now(), "updated_at": _now(), "messages": []}
        self.save(conversation)
        return conversation

    def save(self, conversation: dict[str, Any]) -> None:
        conversation["updated_at"] = _now()
        save_json_atomic(self.root / f"{conversation['conversation_id']}.json", mask_secrets(conversation))

    def load(self, conversation_id: str) -> dict[str, Any] | None:
        path = self.root / f"{Path(conversation_id).name}.json"
        try:
            data = load_json(path, default=None)
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) and isinstance(data.get("messages"), list) else None

    def list(self) -> list[dict[str, Any]]:
        rows = []
        for path in self.root.glob("chat-*.json"):
            try:
                data = load_json(path, default=None)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if isinstance(data, dict) and data.get("conversation_id"):
                rows.append(data)
        return sorted(rows, key=lambda row: row.get("updated_at", ""), reverse=True)

    def add(self, conversation_id: str, *, role: str, content: str, job_id: str = "", engine: str = "commander", status: str = "", result_reference: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        conversation = self.load(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        if role == "user" and status in {"waiting", "planning", "running"} and any(
            row.get("role") == "user"
            and row.get("content") == content
            and row.get("status") in {"waiting", "planning", "running"}
            for row in conversation["messages"]
        ):
            raise ValueError("Duplicate message")
        message = {"message_id": f"msg-{uuid4().hex[:12]}", "role": role, "content": mask_secrets(content), "created_at": _now(), "job_id": job_id, "engine": engine, "status": status, "dry_run": True, "approval_required": True, "execute_allowed": False, "approval_status": "required", "result_reference": result_reference, "metadata": mask_secrets(metadata or {})}
        conversation["messages"].append(message)
        if role == "user" and conversation.get("title") == "新しい会話":
            conversation["title"] = content[:60]
        self.save(conversation)
        return message

    def has_job(self, conversation_id: str, job_id: str) -> bool:
        conversation = self.load(conversation_id) or {}
        return any(row.get("job_id") == job_id for row in conversation.get("messages", []))

    def delete(self, conversation_id: str) -> bool:
        """Delete chat history only. Commander Queue is intentionally untouched."""
        path = self.root / f"{Path(conversation_id).name}.json"
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False

    def sync_job_status(self, conversation_id: str, job_id: str, status: str) -> bool:
        """Persist live job status into chat messages when it changes."""
        conversation = self.load(conversation_id)
        if not conversation or not job_id or not status:
            return False
        changed = False
        for message in conversation.get("messages", []):
            if message.get("job_id") == job_id and message.get("status") != status:
                message["status"] = status
                changed = True
        if changed:
            self.save(conversation)
        return changed


def poll_job(getter: Callable[[str], dict[str, Any] | None], job_id: str, *, timeout: float = 15, interval: float = 1) -> dict[str, Any]:
    deadline = time.monotonic() + max(0, timeout)
    while True:
        job = getter(job_id)
        if job and job.get("status") in TERMINAL:
            return {"timed_out": False, "job": job}
        if time.monotonic() >= deadline:
            return {"timed_out": True, "job": job or {"job_id": job_id, "status": "waiting"}}
        time.sleep(max(0.05, interval))


def enforce_safe_job(job: dict[str, Any]) -> dict[str, Any]:
    return {**job, "dry_run": True, "approval_required": True, "execute_allowed": False, "production_actions_enabled": False}
