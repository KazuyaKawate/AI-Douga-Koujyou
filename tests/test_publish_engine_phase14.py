from __future__ import annotations

from pathlib import Path

from src.publish_engine.analytics_sync import AnalyticsSync
from src.publish_engine.approval_manager import ApprovalManager
from src.publish_engine.oauth_manager import OAuthManager
from src.publish_engine.publish_queue import PublishQueue
from src.publish_engine.publisher import PublishEngine
from src.publish_engine.retry_manager import RetryManager
from src.publish_engine.rollback_manager import RollbackManager
from src.publish_engine.scheduler import PublishScheduler
from src.publish_engine.threads_publisher import ThreadsPublisher
from src.revenue_engine.dashboard import RevenueEngineDashboard


def test_publish_queue_creates_draft_and_blocks_duplicates() -> None:
    queue = PublishQueue()
    state = {"queue": [], "history": []}
    content = {"content_id": "c1", "title": "AIOS投稿", "text": "hello"}
    item = queue.create_item(content, "threads")

    added = queue.add(state, item)
    duplicate = queue.add(state, queue.create_item(content, "threads"))

    assert added["status"] == "draft"
    assert duplicate["status"] == "duplicate_blocked"


def test_approval_manager_requires_review_and_blocks_secret_or_ng_word() -> None:
    manager = ApprovalManager()
    safe = manager.review({"content": {"title": "AIOS", "body": "AIOSの公開結果を分析してKnowledgeへ保存します。" * 3}})
    secret = manager.review({"content": {"body": "api_key=abc123"}})
    ng = manager.review({"content": {"body": "必ず儲かる"}})

    assert safe["requires_review"] is True
    assert safe["status"] == "approved"
    assert secret["status"] == "rejected"
    assert ng["status"] == "rejected"


def test_oauth_status_defaults_to_dry_run(monkeypatch) -> None:
    monkeypatch.delenv("THREADS_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("THREADS_USER_ID", raising=False)

    status = OAuthManager().status("threads")

    assert status["configured"] is False
    assert status["dry_run"] is True
    assert "THREADS_ACCESS_TOKEN" in status["missing"]


def test_platform_publisher_dry_run_supports_threads_image_and_thread_post() -> None:
    item = {"content": {"text": "hello", "image_prompt": "image", "thread": ["reply"]}}

    result = ThreadsPublisher().publish(item, dry_run=True)

    assert result["status"] == "dry_run"
    assert result["image_attached"] is True
    assert result["thread_post"] is True


def test_scheduler_retry_rollback_and_analytics() -> None:
    item = {"publish_id": "p1", "content": {"text": "hello" * 30, "estimated_revenue": 1200}, "attempts": 0}

    scheduled = PublishScheduler().schedule(item)
    retry = RetryManager().queue_retry(item, "error")
    rollback = RollbackManager().create_plan(item, "failed")
    analytics = AnalyticsSync().sync(item)

    assert scheduled["status"] == "scheduled"
    assert retry["status"] == "retry"
    assert rollback["actions"]
    assert analytics["pv"] > 0
    assert analytics["roi"] > 0


def test_publish_engine_full_dry_run_flow_persists_state_and_feedback(tmp_path: Path, monkeypatch) -> None:
    revenue_dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    engine = PublishEngine(path=tmp_path / "publish_engine.json", revenue_dashboard=revenue_dashboard)
    monkeypatch.setattr(engine, "feedback_revenue", lambda item, metrics: {"source": "revenue-test"})
    monkeypatch.setattr(engine, "feedback_business", lambda item, metrics: {"source": "business-test"})
    monkeypatch.setattr(engine, "feedback_coding", lambda item, metrics: {"source": "coding-test"})
    monkeypatch.setattr(engine, "save_knowledge", lambda item, metrics: {"id": "knowledge-test"})

    draft = engine.create_draft({"content_id": "c1", "type": "threads", "title": "AIOS", "text": "AIOS公開テスト本文です。" * 8, "estimated_revenue": 1000}, "threads")
    approved = engine.approve(draft["publish_id"])
    scheduled = engine.schedule(draft["publish_id"])
    result = engine.publish(draft["publish_id"])
    state = engine.load_state()

    assert approved["status"] == "scheduled" or approved["status"] == "approved"
    assert scheduled["status"] == "scheduled"
    assert result["status"] == "dry_run"
    assert state["history"]
    assert state["knowledge_history"][0]["id"] == "knowledge-test"
    assert revenue_dashboard.load_state()["publish_history"][0]["publish_id"] == draft["publish_id"]
    assert result["revenue_feedback"]["source"] == "revenue-test"


def test_publish_engine_rejected_review_creates_rollback(tmp_path: Path) -> None:
    engine = PublishEngine(path=tmp_path / "publish_engine.json")
    draft = engine.create_draft({"content_id": "bad", "type": "note", "title": "bad", "body": "api_key=abc"}, "note")

    result = engine.publish(draft["publish_id"])
    state = engine.load_state()

    assert result["status"] == "rejected"
    assert state["rollbacks"]


def test_publish_engine_blocks_unapproved_safe_draft(tmp_path: Path) -> None:
    engine = PublishEngine(path=tmp_path / "publish_engine.json", revenue_dashboard=RevenueEngineDashboard(path=tmp_path / "revenue_engine.json"))
    draft = engine.create_draft({"content_id": "safe", "type": "threads", "title": "AIOS", "text": "AIOSの安全な投稿本文です。" * 8}, "threads")

    result = engine.publish(draft["publish_id"])
    state = engine.load_state()

    assert result["status"] == "rejected"
    assert result["reason"] == "approval_required"
    assert state["history"] == []
    assert state["rollbacks"]


def test_publish_engine_run_queue_publishes_approved_note_and_threads(tmp_path: Path, monkeypatch) -> None:
    revenue_dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    engine = PublishEngine(path=tmp_path / "publish_engine.json", revenue_dashboard=revenue_dashboard)
    monkeypatch.setattr(engine, "feedback_revenue", lambda item, metrics: {"source": "revenue-test"})
    monkeypatch.setattr(engine, "feedback_business", lambda item, metrics: {"source": "business-test"})
    monkeypatch.setattr(engine, "feedback_coding", lambda item, metrics: {"source": "coding-test"})
    monkeypatch.setattr(engine, "save_knowledge", lambda item, metrics: {"id": f"knowledge-{item['publish_id']}"})
    note = engine.create_draft({"content_id": "note-q", "type": "note", "title": "note公開", "body": "note本文です。" * 8}, "note")
    threads = engine.create_draft({"content_id": "threads-q", "type": "threads", "title": "Threads公開", "text": "Threads本文です。" * 8}, "threads")
    engine.approve(note["publish_id"])
    engine.approve(threads["publish_id"])

    result = engine.run_queue()
    state = engine.load_state()
    revenue_state = revenue_dashboard.load_state()

    assert result["processed"] == 2
    assert result["success"] == 2
    assert {row["platform"] for row in state["history"][:2]} == {"note", "threads"}
    assert len(revenue_state["publish_history"]) == 2
    assert all(row["dry_run"] is True for row in revenue_state["publish_history"])


def test_publish_engine_failed_publish_rolls_back_without_dashboard_update(tmp_path: Path, monkeypatch) -> None:
    class FailedPublisher:
        def publish(self, item, *, dry_run=True):
            return {"status": "failed", "dry_run": dry_run, "message": "api failed"}

    revenue_dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    engine = PublishEngine(path=tmp_path / "publish_engine.json", revenue_dashboard=revenue_dashboard)
    monkeypatch.setattr(engine, "_publisher_for", lambda platform: FailedPublisher())
    draft = engine.create_draft({"content_id": "fail", "type": "threads", "title": "fail", "text": "失敗テスト本文です。" * 8}, "threads")
    engine.approve(draft["publish_id"])

    result = engine.publish(draft["publish_id"])

    assert result["status"] == "failed"
    assert engine.load_state()["history"] == []
    assert engine.load_state()["rollbacks"]
    assert revenue_dashboard.load_state()["publish_history"] == []


def test_publish_engine_dry_run_can_be_disabled_when_oauth_configured(tmp_path: Path, monkeypatch) -> None:
    revenue_dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    engine = PublishEngine(path=tmp_path / "publish_engine.json", revenue_dashboard=revenue_dashboard)
    monkeypatch.setenv("NOTE_ACCESS_TOKEN", "note-token")
    monkeypatch.setattr(engine, "feedback_revenue", lambda item, metrics: {"source": "revenue-test"})
    monkeypatch.setattr(engine, "feedback_business", lambda item, metrics: {"source": "business-test"})
    monkeypatch.setattr(engine, "feedback_coding", lambda item, metrics: {"source": "coding-test"})
    monkeypatch.setattr(engine, "save_knowledge", lambda item, metrics: {"id": "knowledge-test"})
    engine.set_dry_run(False)
    draft = engine.create_draft({"content_id": "live-note", "type": "note", "title": "live", "body": "live本文です。" * 8}, "note")
    engine.approve(draft["publish_id"])

    result = engine.publish(draft["publish_id"])

    assert result["status"] == "manual_ready"
    assert result["result"]["dry_run"] is False
    assert result["result"]["manual_mode"] is True
    assert revenue_dashboard.load_state()["publish_history"][0]["status"] == "manual_ready"


def test_publish_engine_manual_pack_generates_copy_text_and_marks_posted(tmp_path: Path, monkeypatch) -> None:
    revenue_dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    engine = PublishEngine(path=tmp_path / "publish_engine.json", revenue_dashboard=revenue_dashboard)
    monkeypatch.setattr(engine, "feedback_revenue", lambda item, metrics: {"source": "revenue-test"})
    monkeypatch.setattr(engine, "feedback_business", lambda item, metrics: {"source": "business-test"})
    monkeypatch.setattr(engine, "feedback_coding", lambda item, metrics: {"source": "coding-test"})
    monkeypatch.setattr(engine, "save_knowledge", lambda item, metrics: {"id": f"knowledge-{item['publish_id']}"})
    engine.set_dry_run(False)

    drafts = engine.create_manual_pack(
        {"title": "Manual AIOS", "body": "手動投稿モードの本文です。" * 8, "cta": "続きはnoteへ。", "hashtags": "AIOS Threads"},
        priority=90,
    )
    for draft in drafts:
        engine.approve(draft["publish_id"])
        result = engine.publish(draft["publish_id"])
        assert result["status"] == "manual_ready"
        assert result["result"]["copy_text"]
        assert result["result"]["manual_mode"] is True

    posted = engine.mark_posted(drafts[0]["publish_id"], posted_url="https://www.threads.net/@aios/post/1")
    state = engine.load_state()

    assert posted["status"] == "posted"
    assert state["history"][0]["status"] == "posted"
    assert state["history"][0]["posted_url"] == "https://www.threads.net/@aios/post/1"


def test_publish_engine_knowledge_save_preserves_existing(monkeypatch, tmp_path: Path) -> None:
    existing = {"success_examples": [{"id": "old"}], "failure_examples": [], "improvement_examples": [], "timeline": [], "categories": {}}
    saved = {}
    engine = PublishEngine(path=tmp_path / "publish_engine.json")

    monkeypatch.setattr("src.publish_engine.publisher.load_knowledge", lambda: existing)
    monkeypatch.setattr("src.publish_engine.publisher.save_knowledge", lambda data: saved.update(data))
    monkeypatch.setattr("src.publish_engine.publisher.record_improvement", lambda data: {"ok": True})

    record = engine.save_knowledge({"publish_id": "p1", "platform": "threads", "status": "dry_run", "content_id": "c1"}, {"revenue": 100, "roi": 20})

    assert saved["success_examples"][0]["id"] == record["id"]
    assert any(item["id"] == "old" for item in saved["success_examples"])
    assert saved["categories"]["publish_engine"] == 1
