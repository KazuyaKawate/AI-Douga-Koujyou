from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from src.self_builder.knowledge_manager import load_knowledge, save_knowledge


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CodingKnowledgeWriter:
    def save_run(self, run: dict[str, Any]) -> dict[str, Any]:
        knowledge = load_knowledge()
        record = {
            "id": f"ck-{uuid4().hex[:10]}",
            "type": "coding_engine_run",
            "issue": run.get("issue", ""),
            "status": run.get("status", ""),
            "plan_id": run.get("plan", {}).get("plan_id", ""),
            "review": run.get("review", {}),
            "tests_ok": run.get("tests", {}).get("ok", False),
            "commit_candidate": run.get("commit_candidate", {}),
            "roi": run.get("business_evaluation", {}).get("score", {}),
            "created_at": _now(),
        }
        bucket = "success_examples" if record["tests_ok"] and record["review"].get("status") == "approved" else "improvement_examples"
        knowledge.setdefault(bucket, []).insert(0, record)
        knowledge.setdefault("timeline", []).insert(0, record)
        knowledge.setdefault("categories", {}).setdefault("coding_engine", 0)
        knowledge["categories"]["coding_engine"] += 1
        save_knowledge(knowledge)
        return record

    def save_scan(self, scan: dict[str, Any]) -> dict[str, Any]:
        knowledge = load_knowledge()
        record = {
            "id": f"cks-{uuid4().hex[:10]}",
            "type": "coding_engine_auto_scan",
            "scan_id": scan.get("scan_id", ""),
            "summary": scan.get("summary", {}),
            "suggested_next_fix": scan.get("suggested_next_fix", {}),
            "security": {
                "ok": scan.get("security", {}).get("ok", False),
                "high_count": scan.get("security", {}).get("high_count", 0),
            },
            "dependency": {
                "ok": scan.get("dependency", {}).get("ok", False),
                "missing_imports": scan.get("dependency", {}).get("missing_imports", []),
            },
            "created_at": _now(),
        }
        knowledge.setdefault("improvement_examples", []).insert(0, record)
        knowledge.setdefault("timeline", []).insert(0, record)
        knowledge.setdefault("categories", {}).setdefault("coding_engine_scan", 0)
        knowledge["categories"]["coding_engine_scan"] += 1
        save_knowledge(knowledge)
        return record
