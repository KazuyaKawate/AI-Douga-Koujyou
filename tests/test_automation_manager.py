from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.approval import approval_queue
from src.automation.automation_manager import AutomationManager
from src.business_engine.manager import BusinessEngineStore
from src.creator_factory.factory_manager import CreatorFactoryManager
from src.export.export_manager import ExportManager
from src.pipeline.pipeline_manager import PipelineManager


@pytest.fixture()
def automation_env(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(approval_queue, "CONFIG_PATH", tmp_path / "config" / "approval_queue.json")
    monkeypatch.setattr(approval_queue, "OUTPUT_ROOT", tmp_path / "output" / "approval")
    creator = CreatorFactoryManager(tmp_path / "data")
    business = BusinessEngineStore(tmp_path / "config" / "business_engine.json")
    export = ExportManager(tmp_path / "config" / "export_manager.json", tmp_path / "output")
    pipeline = PipelineManager(tmp_path / "data", creator=creator, business=business, export_manager=export)
    automation = AutomationManager(tmp_path / "data", creator=creator, business=business, pipeline=pipeline, export_manager=export)
    return automation, creator, business, pipeline, export


def test_automation_creation_and_lifecycle(automation_env) -> None:
    automation, *_ = automation_env
    rule = automation.create_rule("Daily Creator", "creator_factory", schedule_type="daily")

    assert rule["rule_id"].startswith("auto_")
    assert automation.pause_rule(rule["rule_id"])["status"] == "paused"
    assert automation.resume_rule(rule["rule_id"])["status"] == "enabled"
    assert automation.disable_rule(rule["rule_id"])["status"] == "disabled"
    assert automation.enable_rule(rule["rule_id"])["status"] == "enabled"
    assert automation.delete_rule(rule["rule_id"])["status"] == "deleted"
    assert automation.list_rules() == []


def test_scheduler_due_and_missed_runs(automation_env) -> None:
    automation, *_ = automation_env
    rule = automation.create_rule("Hourly SEO", "seo_blog", schedule_type="hourly")
    data = automation._load_rules()
    data["rules"][0]["next_run"] = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
    automation._save_rules(data)

    due = automation.due_rules()
    missed = automation.detect_missed_runs(datetime.now())

    assert due[0]["rule_id"] == rule["rule_id"]
    assert missed == 1


def test_manual_run_creates_pipeline_and_approval(automation_env) -> None:
    automation, creator, business, pipeline, _export = automation_env
    project = creator.create_project("Automation Project")
    template = creator.create_template("Automation Template", "note_article", "Use local automation context.")
    rule = automation.create_rule(
        "Manual Creator Run",
        "creator_factory",
        project_id=project["id"],
        template_id=template["id"],
        schedule_type="manual",
    )

    execution = automation.manual_run(rule["rule_id"])

    assert execution["status"] == "completed"
    assert execution["pipeline_id"]
    assert execution["approval_id"]
    assert execution["checksum"]
    assert pipeline.get_job(execution["pipeline_id"])["status"] == "pending_review"
    assert business.load()["scheduled_jobs"][0]["payload"]["pipeline_job_id"] == execution["pipeline_id"]


def test_auto_approve_exports_locally(automation_env) -> None:
    automation, _creator, _business, pipeline, export = automation_env
    rule = automation.create_rule("Auto Export", "business_report", auto_approve=True)

    execution = automation.manual_run(rule["rule_id"])

    assert execution["status"] == "completed"
    assert execution["export_id"]
    assert pipeline.get_job(execution["pipeline_id"])["status"] == "completed"
    assert export.summary()["completed_exports"] == 1


def test_retry_failure_recovery(automation_env, monkeypatch) -> None:
    automation, *_ = automation_env
    rule = automation.create_rule("Broken Automation", "sns")
    monkeypatch.setattr(automation.pipeline, "create_production_job", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("local failure")))

    failed = automation.manual_run(rule["rule_id"])
    retry = automation.retry_execution(failed["execution_id"])

    assert failed["status"] == "failed"
    assert retry["status"] == "failed"
    assert retry["retry_of"] == failed["execution_id"]


def test_pause_resume_blocks_scheduled_not_manual(automation_env) -> None:
    automation, *_ = automation_env
    rule = automation.create_rule("Paused Rule", "affiliate", schedule_type="daily")
    automation.pause_rule(rule["rule_id"])

    scheduled = automation.run_rule(rule["rule_id"])
    manual = automation.manual_run(rule["rule_id"])

    assert scheduled["status"] == "cancelled"
    assert manual["status"] == "completed"


def test_history_queue_and_summary(automation_env) -> None:
    automation, *_ = automation_env
    rule = automation.create_rule("Custom Interval", "template_refresh", schedule_type="custom_interval", interval_minutes=5)
    execution = automation.manual_run(rule["rule_id"])
    summary = automation.dashboard_summary()

    assert automation.get_execution(execution["execution_id"])["status"] == "completed"
    assert automation.history()[0]["execution_id"] == execution["execution_id"]
    assert automation.execution_log()
    assert summary["today_runs"] >= 1
    assert summary["local_first"] is True


def test_local_only_verification(automation_env, monkeypatch) -> None:
    def fail_network(*args, **kwargs):
        raise AssertionError("Automation Engine must not call external APIs.")

    monkeypatch.setattr("urllib.request.urlopen", fail_network)
    automation, *_ = automation_env
    rule = automation.create_rule("Local Only", "knowledge_update")
    execution = automation.manual_run(rule["rule_id"])

    assert execution["status"] == "completed"
    assert execution["local_first"] is True
    assert execution["external_apis_enabled"] is False
