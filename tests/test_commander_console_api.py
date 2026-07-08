from __future__ import annotations

from pathlib import Path

from src.commander.api import CommanderAPI
from src.commander.queue import STATUS_APPROVED, STATUS_DRY_RUN_COMPLETE, CommanderQueue
from src.commander.templates import list_templates
from src.commander.worker import CommanderWorker


class PreviewCodingManager:
    def __init__(self) -> None:
        self.runs: list[dict] = []

    def provider_health_probe(self, timeout_seconds: int = 5):
        return [{"provider": "local", "status": "ready", "duration_ms": 1}]

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
        self.runs.append({"apply_approved": apply_approved, "target_files": target_files or []})
        return {
            "run_id": "ce-preview",
            "status": "completed",
            "applied_edits": {
                "status": "preview_locked" if not apply_approved else "applied",
                "applied": bool(apply_approved),
                "preview": {
                    "requires_approval": True,
                    "target_files": target_files or [],
                    "unified_diff": "diff --git a/src/a.py b/src/a.py\n--- a/src/a.py\n+++ b/src/a.py\n",
                },
            },
            "tests": {"ok": True, "results": [{"command": "pytest -q"}]},
            "commit_candidate": {"ready": True},
            "business_evaluation": {"score": {"estimated_revenue": 1000}},
        }


def test_commander_templates_include_revenue_workflows() -> None:
    ids = {template["template_id"] for template in list_templates()}

    assert {"note_article", "threads_post", "official_site", "knowledge_update"} <= ids


def test_dry_run_saves_history_status_and_diff_preview(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config"
    config.mkdir()
    target = tmp_path / "src" / "a.py"
    target.parent.mkdir(parents=True)
    target.write_text("old\n", encoding="utf-8")
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", config / "self_builder_knowledge.json", raising=False)
    queue = CommanderQueue(config / "commander_queue.json")
    queue.enqueue(engine="revenue", instruction="Threads実投稿からPV取得と初クリックを改善", metadata={"target_files": ["src/a.py"]})

    result = CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager()).process_next(dry_run=True)
    history = queue.summary()["history"]

    assert result["status"] == "completed"
    assert history[0]["status"] == STATUS_DRY_RUN_COMPLETE
    assert history[0]["dry_run_result"]["dry_run"] is True
    assert "diff --git" in history[0]["diff_preview"]["unified_diff"]


def test_commander_api_queue_history_approve_execute(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config"
    config.mkdir()
    target = tmp_path / "src" / "a.py"
    target.parent.mkdir(parents=True)
    target.write_text("old\n", encoding="utf-8")
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", config / "self_builder_knowledge.json", raising=False)
    queue = CommanderQueue(config / "commander_queue.json")
    worker = CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager())
    api = CommanderAPI(queue, root=tmp_path, worker=worker)

    enqueued = api.enqueue_template("threads_post")
    assert enqueued["ok"] is True
    assert api.queue_endpoint()["endpoint"] == "/api/commander/queue"

    worker.process_next(dry_run=True)
    job_id = api.history_endpoint()["history"][0]["job_id"]
    approved = api.approve_endpoint(job_id)

    assert approved["ok"] is True
    assert approved["job"]["status"] == STATUS_APPROVED

    executed = api.execute_endpoint(job_id)

    assert executed["endpoint"] == "/api/commander/execute"
    assert executed["result"]["status"] == "completed"
    assert worker.coding_manager.runs[-1]["apply_approved"] is True
