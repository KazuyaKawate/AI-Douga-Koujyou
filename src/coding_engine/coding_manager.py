from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.business_engine.manager import BusinessEngineStore
from src.coding_engine.auto_issue_detector import AutoIssueDetector
from src.coding_engine.continuous_learning import CodingContinuousLearning
from src.coding_engine.knowledge_writer import CodingKnowledgeWriter
from src.coding_engine.provider_router import CodingProviderRouter
from src.coding_engine.task_executor import CodingTaskExecutor
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


CODING_ENGINE_PATH = PROJECT_ROOT / "config" / "coding_engine.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "mode": "local_first",
        "provider_priority": ["ollama", "gemini_cli", "claude_cli", "openai", "ai_router"],
        "history": [],
        "improvement_candidates": [],
        "auto_issue_scans": [],
        "issue_actions": [],
        "revenue_improvement_queue": [],
        "business_manager_feedback": [],
        "provider_health": [],
        "last_run": {},
        "last_scan": {},
        "updated_at": _now(),
    }


class CodingEngineManager:
    def __init__(self, path: str | Path = CODING_ENGINE_PATH, root: str | Path = PROJECT_ROOT) -> None:
        self.path = Path(path)
        self.root = Path(root).resolve(strict=False)

    def load_state(self) -> dict[str, Any]:
        if not self.path.exists():
            state = _default_state()
            self.save_state(state)
            return state
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            data = _default_state()
        if not isinstance(data, dict):
            data = _default_state()
        defaults = _default_state()
        for key, value in defaults.items():
            data.setdefault(key, value)
        return data

    def save_state(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = _now()
        save_json_atomic(self.path, state)

    def provider_status(self) -> list[dict[str, Any]]:
        return CodingProviderRouter(self.load_state().get("provider_priority", [])).status()

    def provider_health_probe(self, timeout_seconds: int = 5) -> list[dict[str, Any]]:
        health = CodingProviderRouter(self.load_state().get("provider_priority", [])).health_probe(timeout_seconds=timeout_seconds)
        state = self.load_state()
        state["provider_health"] = health
        self.save_state(state)
        return health

    def auto_scan(
        self,
        *,
        pytest_log: str = "",
        compile_log: str = "",
        streamlit_log: str = "",
        run_dependency_check: bool = False,
    ) -> dict[str, Any]:
        scan = AutoIssueDetector(self.root).scan(
            pytest_log=pytest_log,
            compile_log=compile_log,
            streamlit_log=streamlit_log,
            run_dependency_check=run_dependency_check,
        )
        scan["knowledge_record"] = CodingKnowledgeWriter().save_scan(scan)
        self._send_scan_to_business_engine(scan)
        state = self.load_state()
        compact = self._compact_scan(scan)
        state["last_scan"] = compact
        state.setdefault("auto_issue_scans", []).insert(0, compact)
        state["auto_issue_scans"] = state["auto_issue_scans"][:50]
        state["improvement_candidates"] = scan.get("issues", [])[:20]
        self.save_state(state)
        return scan

    def apply_issue(self, issue: dict[str, Any], *, run_tests: bool = False) -> dict[str, Any]:
        path = str(issue.get("path", ""))
        targets = [path] if path and Path(path).suffix else []
        return self.run_issue(str(issue.get("instruction") or issue.get("title") or issue.get("message")), target_files=targets, run_tests=run_tests)

    def record_issue_action(self, issue: dict[str, Any], action: str, reason: str = "") -> dict[str, Any]:
        record = {
            "action_id": f"cea-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "action": action,
            "issue_id": issue.get("issue_id", ""),
            "title": issue.get("title", ""),
            "reason": reason,
            "created_at": _now(),
        }
        state = self.load_state()
        state.setdefault("issue_actions", []).insert(0, record)
        state["issue_actions"] = state["issue_actions"][:100]
        self.save_state(state)
        return record

    def run_issue(
        self,
        issue: str,
        *,
        target_files: list[str] | None = None,
        run_tests: bool = False,
        pytest_args: list[str] | None = None,
        apply_approved: bool = False,
        provider_priority: list[str] | None = None,
    ) -> dict[str, Any]:
        executor = CodingTaskExecutor(self.root, provider_priority=provider_priority)
        run = executor.execute(
            issue,
            target_files=target_files,
            run_tests=run_tests,
            pytest_args=pytest_args,
            apply_approved=apply_approved,
        )
        state = self.load_state()
        compact = self._compact_run(run)
        direct_feedback = self._build_business_manager_feedback(compact)
        state["last_run"] = compact
        state.setdefault("history", []).insert(0, compact)
        state["history"] = state["history"][:100]
        state["improvement_candidates"] = CodingContinuousLearning().improvement_candidates(state["history"])
        state.setdefault("revenue_improvement_queue", []).insert(0, direct_feedback)
        state["revenue_improvement_queue"] = state["revenue_improvement_queue"][:100]
        state.setdefault("business_manager_feedback", []).insert(0, direct_feedback)
        state["business_manager_feedback"] = state["business_manager_feedback"][:100]
        self.save_state(state)
        self._send_run_to_business_manager(direct_feedback)
        return run

    def _send_scan_to_business_engine(self, scan: dict[str, Any]) -> None:
        store = BusinessEngineStore()
        data = store.load()
        for issue in scan.get("issues", [])[:10]:
            evaluation = store.evaluate_improvement_roi(
                {
                    "instruction": issue.get("instruction", issue.get("title", "")),
                    "estimated_revenue": issue.get("estimated_revenue", 0),
                    "estimated_effort": issue.get("effort", 20),
                    "risk": issue.get("risk", "medium"),
                    "target_files": [issue.get("path", "")],
                }
            )
            data = store.load()
            data.setdefault("mission_planner_feedback", []).insert(
                0,
                {
                    "source": "coding_engine_auto_scan",
                    "scan_id": scan.get("scan_id", ""),
                    "issue_id": issue.get("issue_id", ""),
                    "status": "candidate",
                    "issue": issue.get("title", ""),
                    "roi": evaluation.get("score", {}),
                    "suggested_target": issue.get("path", ""),
                },
            )
            data["mission_planner_feedback"] = data["mission_planner_feedback"][:100]
            store.save(data)

    @staticmethod
    def _compact_run(run: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": run.get("run_id", ""),
            "status": run.get("status", ""),
            "issue": run.get("issue", ""),
            "plan_id": run.get("plan", {}).get("plan_id", ""),
            "target_files": run.get("plan", {}).get("target_files", []),
            "applied_edits": run.get("applied_edits", {}),
            "revenue_gate": run.get("revenue_gate", {}),
            "review": run.get("review", {}),
            "tests": {"ok": run.get("tests", {}).get("ok", False), "results": run.get("tests", {}).get("results", [])},
            "commit_candidate": run.get("commit_candidate", {}),
            "business_evaluation": run.get("business_evaluation", {}),
            "knowledge_record": run.get("knowledge_record", {}),
            "created_at": _now(),
        }

    @staticmethod
    def _build_business_manager_feedback(run: dict[str, Any]) -> dict[str, Any]:
        gate = run.get("revenue_gate", {})
        score = run.get("business_evaluation", {}).get("score", {})
        return {
            "source": "coding_engine",
            "run_id": run.get("run_id", ""),
            "status": run.get("status", ""),
            "instruction": run.get("issue", ""),
            "target_files": run.get("target_files", []),
            "revenue_gate": gate,
            "roi": score,
            "priority": "high" if gate.get("decision") == "prioritize" else "defer" if gate.get("decision") == "defer" else "review",
            "expected_profit": score.get("estimated_revenue", 0) if isinstance(score, dict) else 0,
            "commit_ready": run.get("commit_candidate", {}).get("ready", False),
            "apply_status": run.get("applied_edits", {}).get("status", ""),
            "created_at": _now(),
        }

    @staticmethod
    def _send_run_to_business_manager(feedback: dict[str, Any]) -> None:
        path = PROJECT_ROOT / "config" / "business_manager.json"
        data = load_json(path, default={}) or {}
        data.setdefault("coding_engine_feedback", []).insert(0, feedback)
        data["coding_engine_feedback"] = data["coding_engine_feedback"][:100]
        data.setdefault("updated_at", _now())
        save_json_atomic(path, data)

    @staticmethod
    def _compact_scan(scan: dict[str, Any]) -> dict[str, Any]:
        return {
            "scan_id": scan.get("scan_id", ""),
            "created_at": scan.get("created_at", _now()),
            "summary": scan.get("summary", {}),
            "issues": scan.get("issues", [])[:50],
            "suggested_next_fix": scan.get("suggested_next_fix", {}),
            "git_status": {
                "entries": scan.get("git_status", {}).get("entries", [])[:100],
                "untracked": scan.get("git_status", {}).get("untracked", [])[:50],
                "production_changes": scan.get("git_status", {}).get("production_changes", [])[:50],
            },
            "security": scan.get("security", {}),
            "dependency": scan.get("dependency", {}),
            "knowledge_record": scan.get("knowledge_record", {}),
        }
