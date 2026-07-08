from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from src.business_engine.manager import BusinessEngineStore
from src.coding_engine.code_editor import CodeEditor
from src.coding_engine.code_generator import CodeGenerator
from src.coding_engine.commit_manager import CommitManager
from src.coding_engine.diff_manager import DiffManager
from src.coding_engine.knowledge_writer import CodingKnowledgeWriter
from src.coding_engine.planner import CodingPlanner
from src.coding_engine.provider_router import CodingProviderRouter
from src.coding_engine.revenue_gate import CommanderRevenueGate
from src.coding_engine.repository_reader import RepositoryReader
from src.coding_engine.review_agent import CodingReviewAgent
from src.coding_engine.test_runner import CodingTestRunner
from src.utils.config import PROJECT_ROOT


class CodingTaskExecutor:
    def __init__(self, root: str | Path = PROJECT_ROOT, provider_priority: list[str] | None = None) -> None:
        self.root = Path(root).resolve(strict=False)
        self.reader = RepositoryReader(self.root)
        self.planner = CodingPlanner()
        self.generator = CodeGenerator(CodingProviderRouter(provider_priority) if provider_priority else None)
        self.editor = CodeEditor(self.root)
        self.diff_manager = DiffManager(self.root)
        self.review_agent = CodingReviewAgent()
        self.test_runner = CodingTestRunner(self.root)
        self.commit_manager = CommitManager(self.root)
        self.knowledge_writer = CodingKnowledgeWriter()
        self.business_store = BusinessEngineStore()
        self.revenue_gate = CommanderRevenueGate()

    def execute(
        self,
        issue: str,
        *,
        target_files: list[str] | None = None,
        run_tests: bool = False,
        pytest_args: list[str] | None = None,
        apply_approved: bool = False,
    ) -> dict[str, Any]:
        repository = self.reader.analyze(issue, target_files)
        plan = self.planner.plan(issue, repository)
        revenue_gate = self.revenue_gate.evaluate(issue, plan.get("target_files", []))
        generated = self.generator.generate_patch_plan(issue, plan, repository)
        test_plan = self.test_runner.dry_run_plan()
        applied_edits = self.editor.apply_generated_patch(
            generated,
            approved=apply_approved,
            target_files=plan.get("target_files", []),
            risks=[plan.get("priority", {}).get("risk", "medium"), revenue_gate.get("decision", "review")],
            test_plan=test_plan,
        )
        edit_plan = self.editor.propose_edits(issue, plan, generated)
        diff = self.diff_manager.diff(plan.get("target_files", []))
        review = self.review_agent.review(issue, plan, diff)
        tests = self.test_runner.run(pytest_args=pytest_args) if run_tests else self.test_runner.dry_run_plan()
        commit_candidate = self.commit_manager.candidate(issue, diff, review, tests)
        business_evaluation = self.business_store.evaluate_improvement_roi(
            {
                "instruction": issue,
                "estimated_revenue": plan.get("priority", {}).get("estimated_revenue", 0),
                "estimated_effort": plan.get("priority", {}).get("effort", 20),
                "risk": plan.get("priority", {}).get("risk", "medium"),
                "target_files": plan.get("target_files", []),
            }
        )
        run = {
            "run_id": f"ce-{uuid4().hex[:10]}",
            "status": "completed" if review.get("status") == "approved" and tests.get("ok") else "needs_attention",
            "issue": issue,
            "repository": repository,
            "plan": plan,
            "revenue_gate": revenue_gate,
            "generated": generated,
            "applied_edits": applied_edits,
            "edit_plan": edit_plan,
            "diff": diff,
            "review": review,
            "tests": tests,
            "commit_candidate": commit_candidate,
            "business_evaluation": business_evaluation,
        }
        run["knowledge_record"] = self.knowledge_writer.save_run(run)
        self._notify_mission_planner(run)
        return run

    def _notify_mission_planner(self, run: dict[str, Any]) -> None:
        data = self.business_store.load()
        feedback = {
            "source": "coding_engine",
            "run_id": run.get("run_id", ""),
            "status": run.get("status", ""),
            "issue": run.get("issue", ""),
            "roi": run.get("business_evaluation", {}).get("score", {}),
            "commit_ready": run.get("commit_candidate", {}).get("ready", False),
        }
        data.setdefault("mission_planner_feedback", []).insert(0, feedback)
        data["mission_planner_feedback"] = data["mission_planner_feedback"][:100]
        self.business_store.save(data)
