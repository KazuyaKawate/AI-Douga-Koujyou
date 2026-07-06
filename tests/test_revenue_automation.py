from __future__ import annotations

from src.business_engine.automation import RevenueAutomation
from src.business_engine.manager import BusinessEngineStore


def test_note_automation_full_local_lifecycle(tmp_path):
    automation = RevenueAutomation(BusinessEngineStore(tmp_path / "business_engine.json"))

    article = automation.generate_article("AI revenue automation", "AI収益化")
    reviewed = automation.review_article(article["article_id"])
    approved = automation.approve_article(article["article_id"])
    queued = automation.queue_article(article["article_id"])
    published = automation.publish_article(article["article_id"])

    data = automation.store.load()

    assert reviewed and reviewed["review"]["score"] >= 80
    assert approved and approved["approved"] is True
    assert queued and queued["status"] == "queued"
    assert published and published["status"] == "published"
    assert any(job["job_type"] == "note_article" for job in data["scheduled_jobs"])
    assert data["execution_history"][0]["status"] == "completed"


def test_sns_automation_generates_schedules_and_publishes(tmp_path):
    automation = RevenueAutomation(BusinessEngineStore(tmp_path / "business_engine.json"))

    posts = automation.generate_sns_posts("local-first business engine")
    assert {post["platform"] for post in posts} == {"x", "threads", "instagram"}

    scheduled = [automation.queue_post(post["post_id"], "2026-07-07") for post in posts]
    published = automation.publish_post(posts[0]["post_id"])
    data = automation.store.load()

    assert all(post and post["status"] == "scheduled" for post in scheduled)
    assert published and published["status"] == "published"
    created_jobs = [
        job for job in data["scheduled_jobs"]
        if job["job_type"] == "sns_post"
        and job.get("payload", {}).get("topic") == "local-first business engine"
    ]
    assert len(created_jobs) == 3


def test_affiliate_automation_tracks_revenue(tmp_path):
    automation = RevenueAutomation(BusinessEngineStore(tmp_path / "business_engine.json"))

    offer = automation.create_affiliate_offer(
        "AIOS Template Pack",
        "https://example.com/aios-template",
        commission_rate=0.2,
        expected_clicks=100,
        conversion_rate=0.05,
        average_order_value=10000,
    )
    linked = automation.insert_affiliate_links("Useful toolkit.", offer["offer_id"])
    clicked = automation.track_click(offer["offer_id"], 20)
    converted = automation.track_conversion(offer["offer_id"], 2)

    assert "ref=" in linked
    assert clicked and clicked["clicks"] == 120
    assert converted and converted["conversions"] == 2
    assert converted["estimated_revenue"] == 12000


def test_seo_automation_builds_queue_calendar_and_rankings(tmp_path):
    automation = RevenueAutomation(BusinessEngineStore(tmp_path / "business_engine.json"))

    first = automation.add_keyword("aios automation", "commercial", "high")
    second = automation.add_keyword("aios business engine", "commercial", "normal")
    clusters = automation.cluster_topics()
    links = automation.build_internal_links()
    calendar = automation.build_content_calendar("2026-07-06")
    ranked = automation.track_ranking(first["seo_id"], 18)
    summary = automation.dashboard_summary()

    assert "aios" in clusters
    assert links
    assert calendar[0]["date"] == "2026-07-06"
    assert ranked and ranked["ranking"]["current"] == 18
    assert summary["seo_queue"] == 2
    assert second["keyword"] in clusters["aios"]
