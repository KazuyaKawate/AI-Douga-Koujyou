from __future__ import annotations

from copy import deepcopy

from src.business_engine.automation import RevenueAutomation
from src.business_engine.manager import BusinessEngineStore
from src.business_engine.threads_automation import ThreadsAutomation


def _patch_knowledge(monkeypatch):
    knowledge = {"history": [], "improvement_examples": []}

    def save_knowledge(updated):
        snapshot = deepcopy(updated)
        knowledge.clear()
        knowledge.update(snapshot)

    monkeypatch.setattr("src.business_engine.automation.load_knowledge", lambda: knowledge)
    monkeypatch.setattr("src.business_engine.automation.save_knowledge", save_knowledge)
    monkeypatch.setattr("src.business_engine.threads_automation.load_knowledge", lambda: knowledge)
    monkeypatch.setattr("src.business_engine.threads_automation.save_knowledge", save_knowledge)
    return knowledge


def test_phase7_generates_threads_from_note_with_cta_hashtags_and_asset(tmp_path, monkeypatch):
    knowledge = _patch_knowledge(monkeypatch)
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    note = RevenueAutomation(store).generate_note_article_pipeline("AIOS Threads Automation")
    threads = ThreadsAutomation(store)

    thread = threads.generate_from_note(note["article_id"])
    data = store.load()

    assert thread is not None
    assert thread["status"] == "draft"
    assert thread["article_id"] == note["article_id"]
    assert thread["summary"]
    assert thread["cta"]
    assert "#Threads" in thread["hashtags"]
    assert thread["image_prompt"]
    assert thread["asset_ref"]["source"] == "phase6_note"
    assert data["post_queue"][0]["thread_id"] == thread["thread_id"]
    assert knowledge["history"][0]["type"] == "threads_automation"


def test_phase7_reservation_duplicate_prevention_and_business_job(tmp_path, monkeypatch):
    _patch_knowledge(monkeypatch)
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    note = RevenueAutomation(store).generate_note_article_pipeline("Threads Duplicate Prevention")
    threads = ThreadsAutomation(store)
    thread = threads.generate_from_note(note["article_id"])

    reservation = threads.reserve_thread(thread["thread_id"], "2026-07-21")
    duplicate = threads.generate_from_note(note["article_id"])
    data = store.load()

    assert reservation is not None
    assert reservation["status"] == "reserved"
    assert duplicate and duplicate["status"] == "duplicate_blocked"
    assert data["threads_reservations"][0]["reservation_id"] == reservation["reservation_id"]
    assert any(job.get("payload", {}).get("thread_id") == thread["thread_id"] for job in data["scheduled_jobs"])


def test_phase7_dryrun_publish_history_metrics_knowledge_and_mission_feedback(tmp_path, monkeypatch):
    knowledge = _patch_knowledge(monkeypatch)
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    note = RevenueAutomation(store).generate_note_article_pipeline("Threads Metrics")
    threads = ThreadsAutomation(store)
    thread = threads.generate_from_note(note["article_id"])
    threads.reserve_thread(thread["thread_id"])

    published = threads.publish_thread(thread["thread_id"])
    metrics = threads.fetch_thread_metrics(thread["thread_id"], pv=900, ctr=0.07, reaction_rate=0.11, click_rate=0.08)
    summary = threads.dashboard_summary()
    data = store.load()

    assert published and published["status"] == "dry_run"
    assert published["api_result"]["dry_run"] is True
    assert metrics and metrics["pv"] == 900
    assert metrics["ctr"] == 0.07
    assert metrics["reaction_rate"] == 0.11
    assert data["threads_history"][0]["thread_id"] == thread["thread_id"]
    assert data["threads_improvements"][0]["thread_id"] == thread["thread_id"]
    assert summary["history"] == 1
    assert summary["dry_run"] is True
    assert summary["reaction_rate"] == 0.11
    assert any(row["type"] == "threads_automation" and row["event"] == "metrics" for row in knowledge["history"])
    assert any(row.get("source") == "threads_automation" for row in data["research_feedback"])
    assert any(row.get("source") == "threads_automation" for row in data["mission_planner_feedback"])
    assert any(row["job_id"] == thread["thread_id"] for row in data["execution_history"])


def test_phase7_generates_three_fortune_posts_with_note_cta_and_reservations(tmp_path, monkeypatch):
    knowledge = _patch_knowledge(monkeypatch)
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    threads = ThreadsAutomation(store)

    result = threads.generate_fortune_note_campaign(
        theme="Threads占い",
        note_url="https://note.com/aios/n/demo",
        scheduled_start="2026-07-20",
    )
    duplicate = threads.generate_fortune_note_campaign(
        theme="Threads占い",
        note_url="https://note.com/aios/n/demo",
        scheduled_start="2026-07-20",
    )
    data = store.load()

    assert result["status"] == "success"
    assert len(result["posts"]) == 3
    assert len(result["reservations"]) == 3
    assert [row["scheduled_for"] for row in result["reservations"]] == ["2026-07-20", "2026-07-21", "2026-07-22"]
    assert all("https://note.com/aios/n/demo" in post["text"] for post in result["posts"])
    assert all(post["source_id"] == "revenue_threads_fortune_campaign" for post in result["posts"])
    assert len([post for post in data["post_queue"] if post.get("source_id") == "revenue_threads_fortune_campaign"]) == 3
    assert len([job for job in data["scheduled_jobs"] if job.get("payload", {}).get("platform") == "threads"]) == 3
    assert duplicate["status"] == "duplicate_blocked"
    assert len(duplicate["blocked"]) == 3
    assert any(row["event"] == "fortune_campaign_generated" for row in knowledge["history"])
