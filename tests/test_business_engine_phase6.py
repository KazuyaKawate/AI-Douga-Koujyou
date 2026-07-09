from __future__ import annotations

from copy import deepcopy

from src.business_engine.automation import RevenueAutomation
from src.business_engine.manager import BusinessEngineStore


def test_phase6_article_generation_creates_markdown_seo_image_and_feedback(tmp_path, monkeypatch):
    knowledge = {"history": [], "improvement_examples": []}

    def save_knowledge(updated):
        snapshot = deepcopy(updated)
        knowledge.clear()
        knowledge.update(snapshot)

    monkeypatch.setattr("src.business_engine.automation.load_knowledge", lambda: knowledge)
    monkeypatch.setattr("src.business_engine.automation.save_knowledge", save_knowledge)

    automation = RevenueAutomation(BusinessEngineStore(tmp_path / "business_engine.json"))
    article = automation.generate_note_article_pipeline("AIOS Phase6 Business Engine", "初心者クリエイター")
    data = automation.store.load()

    assert article["status"] == "draft"
    assert article["research"]["topic"] == "AIOS Phase6 Business Engine"
    assert article["keywords"]
    assert article["outline"]
    assert article["image_prompts"]["eyecatch"]
    assert article["eyecatch"]["status"] == "prompt_ready"
    assert article["seo"]["score"] >= 70
    assert article["markdown_path"]
    assert (tmp_path / "note_markdown" / f"{article['article_id']}.md").exists()
    assert data["article_queue"][0]["article_id"] == article["article_id"]
    assert data["research_feedback"][0]["receiver"] == "Research Team"
    assert data["mission_planner_feedback"][0]["receiver"] == "Mission Planner"
    assert knowledge["history"][0]["type"] == "business_article"


def test_phase6_note_reservation_blocks_duplicate_and_saves_job(tmp_path, monkeypatch):
    monkeypatch.setattr("src.business_engine.automation.load_knowledge", lambda: {"history": [], "improvement_examples": []})
    monkeypatch.setattr("src.business_engine.automation.save_knowledge", lambda updated: None)
    automation = RevenueAutomation(BusinessEngineStore(tmp_path / "business_engine.json"))

    article = automation.generate_note_article_pipeline("Duplicate Prevention")
    reservation = automation.schedule_note_post(article["article_id"], "2026-07-20")
    duplicate = automation.schedule_note_post(article["article_id"], "2026-07-21")
    data = automation.store.load()

    assert reservation is not None
    assert reservation["status"] == "reserved"
    assert reservation["api_result"]["status"] == "disabled_local_first"
    assert duplicate and duplicate["status"] == "duplicate_blocked"
    assert len(data["note_reservations"]) == 1
    assert any(job.get("payload", {}).get("note_reservation_id") == reservation["reservation_id"] for job in data["scheduled_jobs"])


def test_phase6_publish_metrics_history_knowledge_and_revenue(tmp_path, monkeypatch):
    knowledge = {"history": [], "improvement_examples": []}

    def save_knowledge(updated):
        snapshot = deepcopy(updated)
        knowledge.clear()
        knowledge.update(snapshot)

    monkeypatch.setattr("src.business_engine.automation.load_knowledge", lambda: knowledge)
    monkeypatch.setattr("src.business_engine.automation.save_knowledge", save_knowledge)

    automation = RevenueAutomation(BusinessEngineStore(tmp_path / "business_engine.json"))
    article = automation.generate_note_article_pipeline("PV CTR Revenue")
    automation.schedule_note_post(article["article_id"], "2026-07-20")
    published = automation.publish_article(article["article_id"])
    metrics = automation.fetch_article_metrics(article["article_id"], pv=1200, ctr=0.08, revenue=15000)
    summary = automation.dashboard_summary()
    data = automation.store.load()

    assert published and published["status"] == "published"
    assert metrics and metrics["pv"] == 1200
    assert metrics["ctr"] == 0.08
    assert metrics["actual_revenue"] == 15000
    assert data["posting_history"][0]["article_id"] == article["article_id"]
    assert data["daily_kpis"][0]["pv"] == 1200
    assert data["daily_kpis"][0]["ctr"] == 0.08
    assert summary["pv"] >= 1200
    assert summary["ctr"] > 0
    assert summary["article_revenue"] >= 15000
    assert any(row["event"] == "metrics" for row in knowledge["history"])
