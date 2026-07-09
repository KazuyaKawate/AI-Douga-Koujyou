from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.self_builder.knowledge_manager import load_knowledge, save_knowledge
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CallbackRouter:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root)

    def route(self, job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        callback = job.get("callback", {}) or {}
        targets = callback.get("targets") or ["business", "revenue", "growth", "mission_planner", "knowledge", "coding_engine"]
        payload = self._payload(job, result)
        routed: dict[str, Any] = {}
        if "business" in targets or "mission_planner" in targets:
            routed["business"] = self._append("business_engine.json", "mission_planner_feedback", payload)
        if "revenue" in targets:
            routed["revenue"] = self._append("revenue_engine.json", "commander_feedback", payload)
        if "growth" in targets:
            routed["growth"] = self._append("growth_engine.json", "commander_feedback", payload)
        if "coding_engine" in targets:
            routed["coding_engine"] = self._append("coding_engine.json", "commander_callbacks", payload)
        if "knowledge" in targets:
            routed["knowledge"] = self._append_knowledge(payload)
        callback_record = {
            "callback_id": f"cb-{uuid4().hex[:10]}",
            "job_id": job.get("job_id", ""),
            "targets": targets,
            "routed": routed,
            "payload": payload,
            "created_at": _now(),
        }
        save_json_atomic(self.root / "config" / "result_callback.json", callback_record)
        return callback_record

    def _append(self, filename: str, key: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self.root / "config" / filename
        data = load_json(path, default={}) or {}
        data.setdefault(key, []).insert(0, payload)
        data[key] = data[key][:100]
        save_json_atomic(path, data)
        return {"file": str(path), "key": key, "status": "saved"}

    def _append_knowledge(self, payload: dict[str, Any]) -> dict[str, Any]:
        knowledge_path = self.root / "config" / "self_builder_knowledge.json"
        knowledge = load_knowledge(knowledge_path)
        record = {
            "id": f"cmdk-{uuid4().hex[:10]}",
            "type": "commander_callback",
            "payload": payload,
            "created_at": _now(),
        }
        bucket = "success_examples" if payload.get("status") == "completed" else "failure_examples" if payload.get("status") == "failed" else "improvement_examples"
        knowledge.setdefault(bucket, []).insert(0, record)
        knowledge.setdefault("timeline", []).insert(0, record)
        knowledge.setdefault("categories", {}).setdefault("commander", 0)
        knowledge["categories"]["commander"] += 1
        save_knowledge(knowledge, knowledge_path)
        return {"status": "saved", "record_id": record["id"]}

    @staticmethod
    def _payload(job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        run = result.get("coding_run", {})
        return {
            "source": "commander",
            "job_id": job.get("job_id", ""),
            "engine": job.get("engine", ""),
            "instruction": job.get("instruction", ""),
            "status": result.get("status", job.get("status", "")),
            "roi": result.get("roi", {}),
            "business_task": result.get("business_task", job.get("business_task", {})),
            "improvements": result.get("knowledge_record", {}).get("improvements", []),
            "revenue_gate": result.get("revenue_gate", {}),
            "provider_health": result.get("provider_health", []),
            "commit_ready": run.get("commit_candidate", {}).get("ready", False),
            "apply_status": run.get("applied_edits", {}).get("status", ""),
            "dry_run": job.get("dry_run", True),
            "created_at": _now(),
        }
