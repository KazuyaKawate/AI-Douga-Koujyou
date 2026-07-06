from __future__ import annotations

from src.business_engine.manager import BusinessEngineStore
from src.business_engine.worker import BusinessWorker


def test_business_engine_pipeline_and_forecast(tmp_path):
    store = BusinessEngineStore(tmp_path / "business_engine.json")

    item = store.add_revenue_item(
        "Beta launch affiliate article",
        channel="affiliate",
        expected_revenue=10000,
        stage="published",
    )
    assert item["probability"] == 50

    updated = store.update_revenue_stage(item["item_id"], "monetizing")
    assert updated is not None
    assert updated["probability"] == 70

    store.record_daily_kpi("2026-07-06", revenue=3000, articles=1, sns_posts=3, affiliate_clicks=12)
    summary = store.pipeline_summary()
    forecast = store.earnings_forecast(days=30)

    assert summary["open_items"] == 1
    assert summary["weighted_forecast"] == 7000
    assert forecast["forecast_total"] >= 7000


def test_business_engine_scheduler_history_and_retry(tmp_path):
    store = BusinessEngineStore(tmp_path / "business_engine.json")

    job = store.schedule_job("note_article", "Write daily note", "2026-07-06", "high")
    assert job["status"] == "queued"

    running = store.update_job_status(job["job_id"], "running")
    assert running is not None
    assert running["attempts"] == 1

    failed = store.update_job_status(job["job_id"], "failed", "local validation failed")
    assert failed is not None

    data = store.load()
    assert len(data["retry_queue"]) == 1
    retry = store.retry_job(data["retry_queue"][0]["retry_id"])
    assert retry is not None
    assert retry["status"] == "queued"

    execution = store.record_execution(job["job_id"], "failed", "captured failure")
    assert execution["status"] == "failed"
    assert store.load()["execution_history"][0]["execution_id"] == execution["execution_id"]


def test_business_worker_discovers_workflow_bindings(tmp_path):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    worker = BusinessWorker(store, workflow_store_dir=tmp_path / "workflows")

    assert worker.workflow_for_job("note_article") == "social.note_article"
    assert worker.workflow_for_job("sns_post") == "social.x_post"
    assert worker.workflow_for_job("affiliate_publish") == ""


def test_business_worker_processes_local_jobs_and_monitor(tmp_path):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    store.load()
    job = store.schedule_job(
        "affiliate_publish",
        "Publish affiliate draft",
        "2026-07-06",
        payload={"use_workflow": False},
    )

    worker = BusinessWorker(store, workflow_store_dir=tmp_path / "workflows")
    result = worker.execute_job(job["job_id"])

    assert result.status == "completed"
    assert result.job_type == "affiliate_publish"

    data = store.load()
    saved = next(j for j in data["scheduled_jobs"] if j["job_id"] == job["job_id"])
    assert saved["status"] == "completed"
    assert data["execution_history"][0]["status"] == "completed"

    monitor = store.execution_monitor()
    assert monitor["completed"] >= 1
    assert monitor["worker"]["status"] == "idle"


def test_business_worker_auto_retries_failed_local_jobs(tmp_path):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    job = store.schedule_job(
        "sns_post",
        "Retryable SNS job",
        "2026-07-06",
        payload={"force_fail": True, "fail_message": "temporary local failure"},
    )

    worker = BusinessWorker(store, workflow_store_dir=tmp_path / "workflows")
    failed = worker.execute_job(job["job_id"])
    assert failed.status == "failed"
    assert store.load()["retry_queue"]

    queued = worker.queue_failed_retries()
    data = store.load()
    saved = next(j for j in data["scheduled_jobs"] if j["job_id"] == job["job_id"])

    assert queued == 1
    assert saved["status"] == "retry_queued"
