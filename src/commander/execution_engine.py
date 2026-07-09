from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


EXECUTION_STATUSES = {"draft", "review", "approved", "scheduled", "executing", "published", "failed"}
CHANNELS = {"note", "threads", "official_line", "website"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Connector(Protocol):
    def publish(self, action: dict[str, Any]) -> dict[str, Any]: ...

    def schedule(self, action: dict[str, Any]) -> dict[str, Any]: ...

    def cancel(self, action: dict[str, Any]) -> dict[str, Any]: ...

    def retry(self, action: dict[str, Any]) -> dict[str, Any]: ...

    def status(self, action: dict[str, Any]) -> dict[str, Any]: ...


class MockConnector:
    def __init__(self, channel: str) -> None:
        self.channel = channel

    def publish(self, action: dict[str, Any]) -> dict[str, Any]:
        return self._result(action, "published", "mock_publish")

    def schedule(self, action: dict[str, Any]) -> dict[str, Any]:
        return self._result(action, "scheduled", "mock_schedule")

    def cancel(self, action: dict[str, Any]) -> dict[str, Any]:
        return self._result(action, "draft", "mock_cancel")

    def retry(self, action: dict[str, Any]) -> dict[str, Any]:
        return self._result(action, "scheduled", "mock_retry")

    def status(self, action: dict[str, Any]) -> dict[str, Any]:
        return self._result(action, action.get("status", "draft"), "mock_status")

    def _result(self, action: dict[str, Any], status: str, operation: str) -> dict[str, Any]:
        return {
            "ok": True,
            "mock": True,
            "operation": operation,
            "channel": self.channel,
            "action_id": action.get("action_id", ""),
            "status": status,
            "result_url": f"mock://{self.channel}/{action.get('action_id', '')}" if status == "published" else "",
            "created_at": _now(),
        }


class ExecutionEngine:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root)
        self.path = self.root / "config" / "commander_execution.json"

    def load(self) -> dict[str, Any]:
        data = load_json(self.path, default={}) or {}
        data.setdefault("queue", [])
        data.setdefault("history", [])
        data.setdefault("updated_at", _now())
        return data

    def save(self, data: dict[str, Any]) -> None:
        data["updated_at"] = _now()
        save_json_atomic(self.path, data)

    def connector(self, channel: str) -> Connector:
        return MockConnector(channel)

    def create_action_from_task(self, task: dict[str, Any], *, channel: str | None = None) -> dict[str, Any]:
        resolved = channel or self._channel_from_task(task)
        if resolved not in CHANNELS:
            raise ValueError(f"Unsupported execution channel: {resolved}")
        action = {
            "action_id": f"act-{uuid4().hex[:10]}",
            "task_id": task.get("task_id", ""),
            "source_job_id": task.get("job_id", ""),
            "channel": resolved,
            "connector": "mock",
            "title": task.get("title", ""),
            "body": task.get("body", task.get("instruction", "")),
            "cta": task.get("cta", ""),
            "target": task.get("target", "初収益"),
            "expected_revenue": int(task.get("expected_revenue", task.get("expected_income", 0)) or 0),
            "priority_score": float(task.get("priority_score", 0) or 0),
            "publish_time": task.get("publish_time", ""),
            "review_notes": task.get("review_notes", ""),
            "result_url": "",
            "status": "review",
            "approved": bool(task.get("approved") or task.get("status") == "approved"),
            "created_at": _now(),
            "updated_at": _now(),
        }
        data = self.load()
        data["queue"].insert(0, action)
        data["queue"] = data["queue"][:300]
        self.save(data)
        return action

    def schedule(self, action_id: str) -> dict[str, Any]:
        return self._operate(action_id, "schedule", required_approved=True)

    def publish(self, action_id: str) -> dict[str, Any]:
        return self._operate(action_id, "publish", required_approved=True)

    def cancel(self, action_id: str) -> dict[str, Any]:
        return self._operate(action_id, "cancel", required_approved=False)

    def retry(self, action_id: str) -> dict[str, Any]:
        return self._operate(action_id, "retry", required_approved=True)

    def status(self, action_id: str) -> dict[str, Any]:
        return self._operate(action_id, "status", required_approved=False)

    def approve(self, action_id: str, *, review_notes: str = "") -> dict[str, Any] | None:
        data = self.load()
        for action in data["queue"]:
            if action.get("action_id") == action_id and action.get("status") in {"review", "draft"}:
                action["approved"] = True
                action["status"] = "approved"
                action["review_notes"] = review_notes
                action["approved_at"] = _now()
                action["updated_at"] = _now()
                self.save(data)
                return action
        return None

    def summary(self) -> dict[str, Any]:
        data = self.load()
        queue = data.get("queue", [])
        history = data.get("history", [])
        scheduled = [item for item in queue if item.get("status") == "scheduled"]
        publishing = [item for item in queue if item.get("status") == "executing"]
        published = [item for item in history if item.get("status") == "published"]
        failed = [item for item in queue + history if item.get("status") == "failed"]
        retry_queue = [item for item in queue if item.get("status") == "failed" and item.get("approved")]
        next_publish = sorted(
            [item for item in queue if item.get("status") in {"approved", "scheduled"}],
            key=lambda item: (-float(item.get("priority_score", 0)), item.get("created_at", "")),
        )
        return {
            "execution_queue": queue,
            "scheduled": scheduled,
            "publishing": publishing,
            "published": published,
            "failed": failed,
            "retry_queue": retry_queue,
            "next_publish": next_publish[0] if next_publish else None,
            "history": history[:100],
        }

    def _operate(self, action_id: str, operation: str, *, required_approved: bool) -> dict[str, Any]:
        data = self.load()
        for index, action in enumerate(data["queue"]):
            if action.get("action_id") != action_id:
                continue
            if required_approved and not action.get("approved"):
                result = {"ok": False, "error": "Review後のみ実行可能", "action_id": action_id, "status": action.get("status", "review")}
                action["last_result"] = result
                self.save(data)
                return result
            if operation == "publish":
                action["status"] = "executing"
            connector = self.connector(action.get("channel", "website"))
            result = getattr(connector, operation)(action)
            action["status"] = result.get("status", action.get("status", "failed"))
            action["result_url"] = result.get("result_url", action.get("result_url", ""))
            action["last_result"] = result
            action["updated_at"] = _now()
            if action["status"] == "published":
                data["queue"].pop(index)
                data.setdefault("history", []).insert(0, action)
                data["history"] = data["history"][:300]
            self.save(data)
            return result
        return {"ok": False, "error": "Action not found", "action_id": action_id}

    @staticmethod
    def _channel_from_task(task: dict[str, Any]) -> str:
        channel = str(task.get("channel", "")).lower()
        if channel in CHANNELS:
            return channel
        categories = {str(item).lower() for item in task.get("categories", [])}
        if "note" in categories:
            return "note"
        if "threads" in categories:
            return "threads"
        if "official_line" in categories or "line" in categories:
            return "official_line"
        return "website"
