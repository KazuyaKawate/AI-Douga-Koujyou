from __future__ import annotations

from pathlib import Path

from src.commander.callback_router import CallbackRouter
from src.commander.queue import CommanderQueue
from src.commander.scheduler import ROIFirstScheduler
from src.commander.worker import CommanderWorker
from src.utils.json_store import load_json


class FakeCodingManager:
    def __init__(self, *, ok: bool = True) -> None:
        self.ok = ok
        self.runs: list[dict] = []

    def provider_health_probe(self, timeout_seconds: int = 5):
        return [
            {"provider": "claude_cli", "status": "ready", "duration_ms": 1},
            {"provider": "ollama", "status": "missing", "duration_ms": 0},
        ]

    def run_issue(
        self,
        issue,
        *,
        target_files=None,
        run_tests=False,
        pytest_args=None,
        apply_approved=False,
        provider_priority=None,
    ):
        self.runs.append(
            {
                "issue": issue,
                "target_files": target_files,
                "run_tests": run_tests,
                "apply_approved": apply_approved,
                "provider_priority": provider_priority,
            }
        )
        return {
            "run_id": "ce-test",
            "status": "completed" if self.ok else "needs_attention",
            "applied_edits": {"status": "preview_locked", "applied": False},
            "tests": {"ok": self.ok, "results": [{"command": "pytest"}, {"command": "compileall"}]},
            "commit_candidate": {"ready": self.ok},
            "business_evaluation": {"score": {"estimated_revenue": 12000, "constitution_priority_score": 88}},
        }


def test_commander_queue_enqueues_and_selects_highest_priority(tmp_path: Path) -> None:
    queue = CommanderQueue(tmp_path / "commander_queue.json")
    low = queue.enqueue(engine="growth", instruction="note SEO改善", priority=30)
    high = queue.enqueue(engine="revenue", instruction="Threads実投稿からPV取得", priority=90)

    assert low["job_id"] != high["job_id"]
    assert queue.next_job()["job_id"] == high["job_id"]


def test_roi_first_scheduler_allows_revenue_jobs_and_defers_large_low_roi() -> None:
    scheduler = ROIFirstScheduler()

    allowed = scheduler.evaluate({"instruction": "Threads実投稿からPV取得と初クリックを改善"})
    deferred = scheduler.evaluate({"instruction": "設定画面を大型全面刷新する"})

    assert allowed["decision"] == "process"
    assert "threads" in allowed["areas"]
    assert deferred["decision"] == "defer"
    assert deferred["forbidden_large_work"] is True


def test_callback_router_appends_to_engine_files_and_result_callback(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "config").mkdir()
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", tmp_path / "config" / "self_builder_knowledge.json", raising=False)
    router = CallbackRouter(tmp_path)
    job = {"job_id": "cmd-test", "engine": "revenue", "instruction": "note売上改善", "dry_run": True}
    result = {"status": "completed", "revenue_gate": {"score": 90}, "provider_health": [], "coding_run": {}, "roi": {}}

    callback = router.route(job, result)

    assert callback["job_id"] == "cmd-test"
    assert load_json(tmp_path / "config" / "business_engine.json", {})["mission_planner_feedback"][0]["source"] == "commander"
    assert load_json(tmp_path / "config" / "revenue_engine.json", {})["commander_feedback"][0]["job_id"] == "cmd-test"
    assert load_json(tmp_path / "config" / "growth_engine.json", {})["commander_feedback"][0]["job_id"] == "cmd-test"
    assert load_json(tmp_path / "config" / "coding_engine.json", {})["commander_callbacks"][0]["job_id"] == "cmd-test"
    assert load_json(tmp_path / "config" / "result_callback.json", {})["job_id"] == "cmd-test"


def test_commander_worker_processes_one_job_dry_run_and_keeps_apply_locked(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config"
    config.mkdir()
    target = tmp_path / "src" / "business_engine" / "threads_automation.py"
    target.parent.mkdir(parents=True)
    target.write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", config / "self_builder_knowledge.json", raising=False)
    queue = CommanderQueue(config / "commander_queue.json")
    queue.enqueue(
        engine="revenue",
        instruction="Threads実投稿からPV取得と初クリックを改善",
        priority=90,
        metadata={"target_files": ["src/business_engine/threads_automation.py"], "pytest_args": ["-q"]},
    )
    fake = FakeCodingManager(ok=True)

    result = CommanderWorker(queue, root=tmp_path, coding_manager=fake).process_next(dry_run=True)
    summary = queue.summary()

    assert result["status"] == "completed"
    assert fake.runs[0]["run_tests"] is True
    assert fake.runs[0]["apply_approved"] is False
    assert result["coding_run"]["applied_edits"]["status"] == "preview_locked"
    assert summary["completed"] == 1
    assert summary["queued"] == 0


def test_commander_worker_defers_non_revenue_large_job(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", config / "self_builder_knowledge.json", raising=False)
    queue = CommanderQueue(config / "commander_queue.json")
    queue.enqueue(engine="business", instruction="設定画面を大型全面刷新する", priority=99)
    fake = FakeCodingManager(ok=True)

    result = CommanderWorker(queue, root=tmp_path, coding_manager=fake).process_next(dry_run=True)

    assert result["status"] == "deferred"
    assert fake.runs == []
    assert queue.summary()["deferred"] == 1


def test_commander_worker_retries_failed_job_with_rotated_provider(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config"
    config.mkdir()
    target = tmp_path / "src" / "business_engine" / "threads_automation.py"
    target.parent.mkdir(parents=True)
    target.write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", config / "self_builder_knowledge.json", raising=False)
    queue = CommanderQueue(config / "commander_queue.json")
    queue.enqueue(
        engine="revenue",
        instruction="Threads実投稿からPV取得と初クリックを改善",
        priority=90,
        metadata={"target_files": ["src/business_engine/threads_automation.py"]},
    )
    fake = FakeCodingManager(ok=False)

    result = CommanderWorker(queue, root=tmp_path, coding_manager=fake).process_next(dry_run=True)
    next_job = queue.next_job()

    assert result["status"] == "failed"
    assert result["retry"]["queued"] is True
    assert next_job["status"] == "retry_queued"
    assert next_job["retry_count"] == 1
    assert next_job["provider_order"][0] != "claude_cli"
