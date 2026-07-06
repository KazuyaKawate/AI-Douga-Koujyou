from __future__ import annotations

from pathlib import Path

import pytest

from src.approval import approval_queue
from src.business_engine.manager import BusinessEngineStore
from src.creator_factory.factory_manager import CreatorFactoryManager
from src.export.export_manager import ExportManager
from src.pipeline.pipeline_manager import PipelineManager
from src.providers.base_provider import ProviderResult


@pytest.fixture()
def pipeline_env(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(approval_queue, "CONFIG_PATH", tmp_path / "config" / "approval_queue.json")
    monkeypatch.setattr(approval_queue, "OUTPUT_ROOT", tmp_path / "output" / "approval")
    creator = CreatorFactoryManager(tmp_path / "data")
    business = BusinessEngineStore(tmp_path / "config" / "business_engine.json")
    export = ExportManager(tmp_path / "config" / "export_manager.json", tmp_path / "output")
    manager = PipelineManager(tmp_path / "data", creator=creator, business=business, export_manager=export)
    return manager, creator, business, export


def test_pipeline_creation(pipeline_env) -> None:
    manager, creator, business, _export = pipeline_env
    project = creator.create_project("Pipeline Project")
    template = creator.create_template("Note Template", "note_article", "Write a useful article.")

    job = manager.create_production_job("note", "Local Note", project_id=project["id"], template_id=template["id"])

    assert job["status"] == "queued"
    assert job["project"] == project["id"]
    assert job["template"] == template["id"]
    assert job["business_job_id"]
    assert business.load()["scheduled_jobs"][0]["payload"]["pipeline_job_id"] == job["job_id"]
    assert (manager.pipeline_dir / f"{job['job_id']}.json").exists()


def test_pipeline_execution_and_approval_handoff(pipeline_env) -> None:
    manager, _creator, _business, _export = pipeline_env
    job = manager.create_production_job("seo_blog", "SEO Draft")

    generated = manager.execute_selected_template(job["job_id"])

    assert generated["status"] == "pending_review"
    assert generated["generated_files"]
    assert generated["checksum"]
    reviews = approval_queue.get_content_reviews("pending_review")
    assert len(reviews) == 1
    assert reviews[0]["source_job_id"] == job["job_id"]
    assert reviews[0]["content_type"] == "seo_article"


def test_export_handoff_completes_pipeline(pipeline_env) -> None:
    manager, creator, business, export = pipeline_env
    job = manager.create_production_job("affiliate", "Affiliate Draft")
    manager.execute_selected_template(job["job_id"])

    approved = manager.approve_pipeline_job(job["job_id"])
    completed = manager.export_pipeline_job(job["job_id"])

    assert approved["status"] == "publish_ready"
    assert completed["status"] == "completed"
    assert completed["export_result"]["export_status"] == "completed"
    assert Path(completed["export_result"]["export_path"]).exists()
    assert creator.list_production()[0]["export_status"] == "exported"
    assert business.load()["scheduled_jobs"][0]["status"] == "completed"
    assert export.summary()["completed_exports"] == 1


def test_retry_cancel_resume_and_pause(pipeline_env) -> None:
    manager, _creator, _business, _export = pipeline_env
    job = manager.create_production_job("sns", "SNS Draft")

    manager.pause()
    with pytest.raises(RuntimeError):
        manager.execute_selected_template(job["job_id"])
    manager.resume()
    cancelled = manager.cancel(job["job_id"])
    retried = manager.retry(job["job_id"])

    assert cancelled["status"] == "cancelled"
    assert retried["status"] == "queued"
    assert manager.is_paused() is False


def test_history_and_dashboard_summary(pipeline_env) -> None:
    manager, _creator, _business, _export = pipeline_env
    job = manager.create_production_job("business_report", "Weekly Report")
    manager.run_full_local(job["job_id"], auto_approve=True)

    saved = manager.get_job(job["job_id"])
    summary = manager.dashboard_summary()

    assert saved is not None
    assert saved["status"] == "completed"
    assert saved["stage_timestamps"]["completed"]
    assert summary["completed_jobs"] == 1
    assert summary["success_rate"] == 100.0
    assert summary["local_first"] is True
    assert summary["external_apis_enabled"] is False


def test_failure_recovery(pipeline_env, monkeypatch) -> None:
    manager, _creator, _business, _export = pipeline_env
    job = manager.create_production_job("note", "Broken Draft")

    monkeypatch.setattr(manager, "_write_generated_content", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("local write failed")))
    failed = manager.execute_selected_template(job["job_id"])
    retried = manager.retry(job["job_id"])

    assert failed["status"] == "failed"
    assert "local write failed" in failed["last_error"]
    assert retried["status"] == "queued"


def test_local_only_verification(pipeline_env, monkeypatch) -> None:
    def fail_network(*args, **kwargs):
        raise AssertionError("No external API calls are allowed.")

    monkeypatch.setattr("urllib.request.urlopen", fail_network)
    manager, _creator, _business, _export = pipeline_env
    job = manager.create_production_job("note", "Local Only")
    completed = manager.run_full_local(job["job_id"], auto_approve=True)

    assert completed["status"] == "completed"
    assert completed["local_first"] is True
    assert completed["external_apis_enabled"] is False


def test_pipeline_generation_uses_provider_registry(pipeline_env) -> None:
    class FakeRegistry:
        def complete(self, prompt: str, **_kwargs):
            assert "Generate a local-first draft" in prompt
            return ProviderResult(
                ok=True,
                content="# Provider Draft\n\nGenerated through registry.",
                provider="virtual",
                model="virtual-test",
                input_tokens=10,
                output_tokens=8,
                external_request=False,
                metadata={"duration_ms": 7},
            )

    manager, _creator, business, _export = pipeline_env
    manager.provider_registry = FakeRegistry()
    job = manager.create_production_job("note", "Provider Routed Draft")

    generated = manager.execute_selected_template(job["job_id"])

    assert generated["status"] == "pending_review"
    assert generated["runtime"] == "virtual"
    assert generated["generation_time_ms"] == 7
    assert generated["input_tokens"] == 10
    assert generated["output_tokens"] == 8
    runtime_logs = business.load()["ai_runtime"]["runtime_logs"]
    assert runtime_logs[0]["total_tokens"] == 18
