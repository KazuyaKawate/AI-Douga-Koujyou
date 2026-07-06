from __future__ import annotations

from pathlib import Path

from src.approval import approval_queue
from src.approval.risk_analyzer import analyze_content_risk
from src.business_engine.manager import BusinessEngineStore
from src.business_engine.worker import BusinessWorker
from src.providers.gemini_cli_provider import GeminiCLIResult


def _patch_queue_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(approval_queue, "CONFIG_PATH", tmp_path / "approval_queue.json")
    monkeypatch.setattr(approval_queue, "OUTPUT_ROOT", tmp_path / "output")


def test_create_approval_content_item(monkeypatch, tmp_path):
    _patch_queue_paths(monkeypatch, tmp_path)

    item = approval_queue.create_content_review_item(
        "Local note",
        "This is a local-first note article with enough useful content for review.",
        "note_article",
        source_job_id="job_1",
    )

    assert item["status"] == "pending_review"
    assert item["content_type"] == "note_article"
    assert approval_queue.content_review_summary()["pending_reviews"] == 1


def test_approve_reject_and_revision_content_item(monkeypatch, tmp_path):
    _patch_queue_paths(monkeypatch, tmp_path)

    approve = approval_queue.create_content_review_item("Approve", "Content for approval review.", "sns_post")
    reject = approval_queue.create_content_review_item("Reject", "Content for rejection review.", "seo_article")
    revise = approval_queue.create_content_review_item("Revise", "Content for revision review.", "business_report")

    assert approval_queue.approve_content_item(approve["id"], "looks good")["status"] == "approved"
    assert approval_queue.reject_content_item(reject["id"], "not suitable")["status"] == "rejected"
    assert approval_queue.request_content_revision(revise["id"], "expand examples")["status"] == "revision_requested"

    summary = approval_queue.content_review_summary()
    assert summary["approved_today"] == 1
    assert summary["rejected_today"] == 1
    assert summary["revision_requested"] == 1


def test_content_risk_flag_detection():
    flags = analyze_content_risk(
        "Guaranteed revenue from this product. Contact me at test@example.com. https://example.com",
        "affiliate_description",
    )
    codes = {flag["code"] for flag in flags}

    assert "money_earnings_claim" in codes
    assert "personal_information_pattern" in codes
    assert "url_pattern" in codes
    assert "affiliate_disclosure_missing" in codes


def test_export_approved_content_item(monkeypatch, tmp_path):
    _patch_queue_paths(monkeypatch, tmp_path)
    item = approval_queue.create_content_review_item(
        "Approved export",
        "Approved local content for markdown and json export.",
        "business_report",
    )
    approval_queue.approve_content_item(item["id"], "approved")

    paths = approval_queue.export_content_item(item["id"], "approved")

    assert paths is not None
    assert paths["markdown"].exists()
    assert paths["json"].exists()
    assert "Approved export" in paths["markdown"].read_text(encoding="utf-8")


def test_business_engine_gemini_output_enters_approval_queue(monkeypatch, tmp_path):
    _patch_queue_paths(monkeypatch, tmp_path)

    class FakeGeminiCLIProvider:
        def __init__(self, **kwargs):
            pass

        def execute_prompt(self, prompt):
            return GeminiCLIResult(
                ok=True,
                prompt=prompt,
                response="Generated article content for human approval review before local export.",
                duration_ms=20,
                input_tokens=5,
                output_tokens=10,
                attempts=1,
            )

    monkeypatch.setattr("src.business_engine.worker.GeminiCLIProvider", FakeGeminiCLIProvider)
    monkeypatch.chdir(tmp_path)
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    job = store.schedule_runtime_job("gemini_note_article", "Approval-gated article", "Write article")

    result = BusinessWorker(store, workflow_store_dir=tmp_path / "workflows").execute_job(job["job_id"])
    reviews = approval_queue.get_content_reviews("pending_review")

    assert result.status == "completed"
    assert len(reviews) == 1
    assert reviews[0]["source_job_id"] == job["job_id"]
    assert reviews[0]["content_type"] == "note_article"


def test_no_external_api_call_path(monkeypatch, tmp_path):
    _patch_queue_paths(monkeypatch, tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    item = approval_queue.create_content_review_item("Local only", "Local content only.", "sns_post")
    approval_queue.approve_content_item(item["id"], "approved locally")

    assert item["status"] == "pending_review"
    assert approval_queue.content_review_summary()["approved_today"] == 1
