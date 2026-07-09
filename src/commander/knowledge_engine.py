from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.self_builder.knowledge_manager import load_knowledge, save_knowledge
from src.utils.config import PROJECT_ROOT


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CommanderKnowledgeEngine:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root)
        self.path = self.root / "config" / "self_builder_knowledge.json"

    def record_result(self, job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        knowledge = load_knowledge(self.path)
        task = result.get("business_task") or job.get("business_task") or job.get("plan", {}).get("business_task", {})
        status = result.get("status", job.get("status", ""))
        record = {
            "id": f"cmdk-{uuid4().hex[:10]}",
            "type": "commander_learning",
            "job_id": job.get("job_id", ""),
            "instruction": job.get("instruction", ""),
            "status": status,
            "success": status == "completed",
            "failure": status in {"failed", "rejected", "deferred"},
            "improvements": self.improvements(job, result),
            "roi": task.get("roi", result.get("metrics", {}).get("roi", 0)),
            "expected_income": task.get("expected_income", task.get("expected_revenue", 0)),
            "task_type": task.get("task_type", ""),
            "created_at": _now(),
        }
        bucket = "success_examples" if record["success"] else "failure_examples" if record["failure"] else "improvement_examples"
        knowledge.setdefault(bucket, []).insert(0, record)
        knowledge.setdefault("commander_learning", []).insert(0, record)
        knowledge.setdefault("timeline", []).insert(0, record)
        knowledge.setdefault("categories", {}).setdefault("commander", 0)
        knowledge["categories"]["commander"] += 1
        knowledge["commander_learning"] = knowledge["commander_learning"][:300]
        knowledge["timeline"] = knowledge["timeline"][:500]
        save_knowledge(knowledge, self.path)
        return record

    @staticmethod
    def improvements(job: dict[str, Any], result: dict[str, Any]) -> list[str]:
        findings = result.get("risk_scan", {}).get("findings", []) + result.get("guard", {}).get("findings", [])
        if result.get("status") == "completed":
            return ["成功パターンを同カテゴリの収益Taskへ再利用する", "ROIが高い導線を次のnote/Threads/Website改善へ展開する"]
        if findings:
            return ["禁止Scopeを除外して再計画する", "対象ファイルを収益導線に限定する", "DryRun差分を小さく分割する"]
        return ["ROIを上げるためnote/Threads/Websiteへ再スコープする", "工数を半分に分割する", "Provider順序を変えて再DryRunする"]

    def growth_summary(self) -> dict[str, Any]:
        knowledge = load_knowledge(self.path)
        records = knowledge.get("commander_learning", [])
        return {
            "records": len(records),
            "success": len([item for item in records if item.get("success")]),
            "failure": len([item for item in records if item.get("failure")]),
            "latest": records[0] if records else {},
        }
