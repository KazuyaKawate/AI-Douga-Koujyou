from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.publish_engine.publisher import PUBLISH_ENGINE_PATH
from src.publish_engine.publish_queue import PublishQueue
from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.utils.json_store import load_json, save_json_atomic


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RevenuePublishApprovalFlow:
    def __init__(
        self,
        *,
        dashboard: RevenueEngineDashboard | None = None,
        publish_path: str | Path = PUBLISH_ENGINE_PATH,
    ) -> None:
        self.dashboard = dashboard or RevenueEngineDashboard()
        self.publish_path = Path(publish_path)
        self.publish_queue = PublishQueue()

    def sync_candidates(self) -> list[dict[str, Any]]:
        state = self.dashboard.load_state()
        existing = {row.get("source_key"): row for row in state.get("publish_approval_candidates", [])}
        candidates = []
        for row in state.get("note_draft_saves", []):
            candidate = self._candidate_from_note(row, existing.get(self._source_key("note", row)))
            candidates.append(candidate)
        for row in state.get("threads_waiting_posts", []):
            candidate = self._candidate_from_threads(row, existing.get(self._source_key("threads", row)))
            candidates.append(candidate)
        state["publish_approval_candidates"] = candidates[:100]
        self.dashboard.save_state(state)
        return state["publish_approval_candidates"]

    def approve(self, candidate_id: str, *, reviewer: str = "human") -> dict[str, Any] | None:
        state = self.dashboard.load_state()
        candidate = next((row for row in state.get("publish_approval_candidates", []) if row.get("candidate_id") == candidate_id), None)
        if candidate is None:
            return None
        candidate["status"] = "approved"
        candidate["approved_by"] = reviewer
        candidate["approved_at"] = _now()
        moved = self.move_to_publish_queue(candidate)
        candidate["publish_queue_item"] = {
            "publish_id": moved.get("publish_id", ""),
            "status": moved.get("status", ""),
            "dry_run": moved.get("dry_run", True),
        }
        state.setdefault("publish_approval_history", []).insert(0, dict(candidate))
        state["publish_approval_history"] = state["publish_approval_history"][:100]
        self.dashboard.save_state(state)
        return candidate

    def move_to_publish_queue(self, candidate: dict[str, Any]) -> dict[str, Any]:
        publish_state = self._load_publish_state()
        item = self.publish_queue.create_item(candidate["content"], candidate["platform"], priority=80)
        item["status"] = "approved"
        item["approval"] = {
            "status": "approved",
            "reviewer": candidate.get("approved_by", "human"),
            "approved_at": candidate.get("approved_at", _now()),
            "dry_run_only": True,
        }
        item["review"] = {"status": "approved", "source": "manual_revenue_publish_approval"}
        item["dry_run"] = True
        added = self.publish_queue.add(publish_state, item)
        publish_state["dry_run_default"] = True
        publish_state.setdefault("logs", []).insert(
            0,
            {
                "event": "manual_approval_to_publish_queue",
                "candidate_id": candidate.get("candidate_id", ""),
                "publish_id": added.get("publish_id", ""),
                "platform": candidate.get("platform", ""),
                "dry_run": True,
                "created_at": _now(),
            },
        )
        self._save_publish_state(publish_state)
        return added

    def _candidate_from_note(self, row: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
        source_key = self._source_key("note", row)
        return {
            "candidate_id": (existing or {}).get("candidate_id", f"cand-{uuid4().hex[:10]}"),
            "source_key": source_key,
            "source": "note_draft",
            "platform": "note",
            "status": (existing or {}).get("status", "approval_waiting"),
            "title": row.get("title", ""),
            "save_url": row.get("save_url", ""),
            "dry_run": True,
            "content": {
                "content_id": row.get("content_id", source_key),
                "type": "note",
                "title": row.get("title", ""),
                "body": row.get("body", ""),
                "draft_url": row.get("save_url", ""),
                "estimated_revenue": row.get("estimated_revenue", 0),
            },
            "created_at": (existing or {}).get("created_at", _now()),
        }

    def _candidate_from_threads(self, row: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
        source_key = self._source_key("threads", row)
        return {
            "candidate_id": (existing or {}).get("candidate_id", f"cand-{uuid4().hex[:10]}"),
            "source_key": source_key,
            "source": "threads_waiting",
            "platform": "threads",
            "status": (existing or {}).get("status", "approval_waiting"),
            "title": row.get("note_title", "Threads投稿候補"),
            "note_save_url": row.get("note_save_url", ""),
            "dry_run": True,
            "content": {
                "content_id": row.get("waiting_id", source_key),
                "type": "threads",
                "title": row.get("note_title", "Threads投稿候補"),
                "text": row.get("text", ""),
                "note_save_url": row.get("note_save_url", ""),
            },
            "created_at": (existing or {}).get("created_at", _now()),
        }

    @staticmethod
    def _source_key(platform: str, row: dict[str, Any]) -> str:
        return f"{platform}:{row.get('flow_id') or row.get('waiting_id') or row.get('content_id') or row.get('save_url') or row.get('note_save_url')}"

    def _load_publish_state(self) -> dict[str, Any]:
        data = load_json(self.publish_path, default={})
        if not isinstance(data, dict):
            data = {}
        data.setdefault("enabled", True)
        data.setdefault("dry_run_default", True)
        data.setdefault("queue", [])
        data.setdefault("history", [])
        data.setdefault("logs", [])
        return data

    def _save_publish_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = _now()
        save_json_atomic(self.publish_path, state)
