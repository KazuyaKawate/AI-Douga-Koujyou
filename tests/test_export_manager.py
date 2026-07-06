from __future__ import annotations

import zipfile

import pytest

from src.approval import approval_queue
from src.export.export_manager import ExportManager, checksum_file


def _patch_approval_queue(monkeypatch, tmp_path):
    monkeypatch.setattr(approval_queue, "CONFIG_PATH", tmp_path / "approval_queue.json")
    monkeypatch.setattr(approval_queue, "OUTPUT_ROOT", tmp_path / "approval_output")


def _publish_ready_item(monkeypatch, tmp_path, content_type="note_article"):
    _patch_approval_queue(monkeypatch, tmp_path)
    item = approval_queue.create_content_review_item(
        "Exportable content",
        "This approved content is ready for a completely local export pipeline.",
        content_type,
        source_job_id="job_export",
    )
    approval_queue.approve_content_item(item["id"], "approved locally")
    return approval_queue.mark_content_publish_ready(item["id"], "ready for export")


def _manager(tmp_path):
    return ExportManager(tmp_path / "export_manager.json", tmp_path / "output")


def test_export_queue_accepts_publish_ready_only(monkeypatch, tmp_path):
    item = _publish_ready_item(monkeypatch, tmp_path)
    manager = _manager(tmp_path)

    record = manager.queue_export(item["id"])

    assert record["content_id"] == item["id"]
    assert record["export_status"] == "queued"


def test_export_queue_rejects_non_publish_ready(monkeypatch, tmp_path):
    _patch_approval_queue(monkeypatch, tmp_path)
    item = approval_queue.create_content_review_item("Draft", "Pending review content.", "sns_post")
    manager = _manager(tmp_path)

    with pytest.raises(ValueError):
        manager.queue_export(item["id"])


def test_markdown_and_json_export(monkeypatch, tmp_path):
    item = _publish_ready_item(monkeypatch, tmp_path, "seo_article")
    manager = _manager(tmp_path)
    record = manager.queue_export(item["id"])

    exported = manager.export_one(record["export_id"])

    assert exported is not None
    assert exported["export_status"] == "completed"
    md_path = tmp_path / "output" / "export" / "seo"
    assert list(md_path.glob("*.md"))
    assert list(md_path.glob("*.json"))


def test_checksum_generation(monkeypatch, tmp_path):
    item = _publish_ready_item(monkeypatch, tmp_path, "business_report")
    manager = _manager(tmp_path)
    record = manager.queue_export(item["id"])
    exported = manager.export_one(record["export_id"])

    assert exported and exported["checksum"]
    assert exported["checksum"] == checksum_file(exported["export_path"])


def test_export_history_and_clear_completed(monkeypatch, tmp_path):
    item = _publish_ready_item(monkeypatch, tmp_path, "sns_post")
    manager = _manager(tmp_path)
    record = manager.queue_export(item["id"])
    manager.export_one(record["export_id"])

    summary = manager.summary()
    assert summary["completed_exports"] == 1
    assert summary["history"]
    assert manager.clear_completed_exports() == 1
    assert manager.summary()["completed_exports"] == 0


def test_export_retry(monkeypatch, tmp_path):
    item = _publish_ready_item(monkeypatch, tmp_path, "affiliate_description")
    manager = _manager(tmp_path)
    record = manager.queue_export(item["id"])

    approval_queue.reject_content_item(item["id"], "simulate no longer ready")
    failed = manager.export_one(record["export_id"])
    assert failed and failed["export_status"] == "failed"

    approval_queue.mark_content_publish_ready(item["id"], "ready again")
    retried = manager.retry_export(record["export_id"])
    assert retried and retried["export_status"] == "completed"


def test_package_builder(monkeypatch, tmp_path):
    item = _publish_ready_item(monkeypatch, tmp_path, "note_article")
    manager = _manager(tmp_path)

    package = manager.build_package([item["id"]])

    assert package["zip_path"].endswith(".zip")
    assert package["checksum"]
    with zipfile.ZipFile(package["zip_path"]) as archive:
        names = set(archive.namelist())
    assert "metadata.json" in names
    assert "manifest.json" in names


def test_business_engine_export_metrics(monkeypatch, tmp_path):
    item = _publish_ready_item(monkeypatch, tmp_path, "business_report")
    manager = _manager(tmp_path)
    record = manager.queue_export(item["id"])
    manager.export_one(record["export_id"])

    summary = manager.summary()
    assert summary["completed_exports"] == 1
    assert summary["total_local_packages"] == 0


def test_no_external_api_path(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    item = _publish_ready_item(monkeypatch, tmp_path, "sns_post")
    manager = _manager(tmp_path)

    record = manager.queue_export(item["id"])
    exported = manager.export_one(record["export_id"])

    assert exported and exported["export_status"] == "completed"
    assert manager.load()["meta"]["external_publish_enabled"] is False
