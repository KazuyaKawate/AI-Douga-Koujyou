from __future__ import annotations

import subprocess

from src.business_engine.manager import BusinessEngineStore
from src.business_engine.scheduler_daemon import SchedulerDaemon
from src.business_engine.worker import BusinessWorker
from src.providers.gemini_cli_provider import GeminiCLIProvider, GeminiCLIResult
from src.approval import approval_queue


def _patch_approval_queue(monkeypatch, tmp_path):
    monkeypatch.setattr(approval_queue, "CONFIG_PATH", tmp_path / "approval_queue.json")
    monkeypatch.setattr(approval_queue, "OUTPUT_ROOT", tmp_path / "output")


def test_gemini_cli_provider_executes_prompt_with_fake_runner(tmp_path):
    def fake_runner(command, **kwargs):
        assert "-p" in command
        return subprocess.CompletedProcess(command, 0, stdout="Generated local article", stderr="")

    provider = GeminiCLIProvider(
        command_path="gemini",
        timeout_seconds=5,
        retries=1,
        log_dir=tmp_path,
        runner=fake_runner,
    )
    result = provider.execute_prompt("Write an article")

    assert result.ok is True
    assert result.response == "Generated local article"
    assert result.estimated_cost_yen == 0
    assert result.input_tokens > 0
    assert result.output_tokens > 0


def test_gemini_cli_provider_handles_timeout_with_fake_runner(tmp_path):
    def timeout_runner(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=1)

    provider = GeminiCLIProvider(
        command_path="gemini",
        timeout_seconds=1,
        retries=2,
        log_dir=tmp_path,
        runner=timeout_runner,
    )
    result = provider.execute_prompt("Write a post")

    assert result.ok is False
    assert result.timed_out is True
    assert result.attempts == 2
    assert "timed out" in result.error


def test_business_worker_executes_gemini_runtime_job(monkeypatch, tmp_path):
    _patch_approval_queue(monkeypatch, tmp_path)

    class FakeGeminiCLIProvider:
        def __init__(self, **kwargs):
            pass

        def execute_prompt(self, prompt):
            return GeminiCLIResult(
                ok=True,
                prompt=prompt,
                response="Runtime output",
                duration_ms=25,
                input_tokens=5,
                output_tokens=7,
                attempts=1,
            )

    monkeypatch.setattr("src.business_engine.worker.GeminiCLIProvider", FakeGeminiCLIProvider)
    monkeypatch.chdir(tmp_path)
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    job = store.schedule_runtime_job("gemini_note_article", "Runtime note", "Write a note article")

    result = BusinessWorker(store, workflow_store_dir=tmp_path / "workflows").execute_job(job["job_id"])
    data = store.load()
    runtime_summary = store.ai_runtime_summary()

    assert result.status == "completed"
    assert result.workflow_name == "gemini_cli"
    assert runtime_summary["completed_jobs"] == 1
    assert runtime_summary["average_cost_yen"] == 0
    assert data["ai_runtime"]["prompt_queue"][0]["status"] == "completed"


def test_scheduler_executes_gemini_runtime_jobs_only_through_cli(monkeypatch, tmp_path):
    _patch_approval_queue(monkeypatch, tmp_path)

    class FakeGeminiCLIProvider:
        def __init__(self, **kwargs):
            pass

        def execute_prompt(self, prompt):
            return GeminiCLIResult(
                ok=True,
                prompt=prompt,
                response="Business report",
                duration_ms=30,
                input_tokens=6,
                output_tokens=8,
                attempts=1,
            )

    monkeypatch.setattr("src.business_engine.worker.GeminiCLIProvider", FakeGeminiCLIProvider)
    monkeypatch.chdir(tmp_path)
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    store.schedule_runtime_job("gemini_business_report", "Runtime report", "Write a business report")
    scheduler = SchedulerDaemon(store)
    scheduler.start()

    state = scheduler.tick(force=True)

    assert "Completed Gemini CLI runtime job" in state["last_result"]
    assert store.ai_runtime_summary()["completed_jobs"] == 1
