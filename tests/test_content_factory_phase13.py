from __future__ import annotations

from pathlib import Path

from src.content_factory.ab_testing import ABTesting
from src.content_factory.analytics import ContentAnalytics
from src.content_factory.content_manager import ContentFactoryManager
from src.content_factory.fortune_engine import FortuneEngine
from src.content_factory.image_prompt_builder import ImagePromptBuilder
from src.content_factory.landing_page_builder import LandingPageBuilder
from src.content_factory.note_builder import NoteBuilder
from src.content_factory.quality_reviewer import QualityReviewer
from src.content_factory.scheduler import ContentScheduler
from src.content_factory.seo_optimizer import SEOOptimizer
from src.content_factory.threads_builder import ThreadsBuilder
from src.content_factory.youtube_summary import YouTubeSummary
from src.business_engine.manager import BusinessEngineStore


def test_note_generator_builds_templates_cta_and_seo_article() -> None:
    note = NoteBuilder().build("AI副業", template="comparison", keywords=["AI副業", "比較"])

    assert note["type"] == "note"
    assert "AI副業" in note["title"]
    assert note["cta"]
    assert any("比較" in section["heading"] for section in note["sections"])


def test_threads_generator_and_fortune_engine_daily_ranking() -> None:
    thread = ThreadsBuilder().build("今日の占い", genre="fortune")
    fortune = FortuneEngine().daily(seed=1)

    assert thread["type"] == "threads"
    assert "#占い" in thread["text"]
    assert len(fortune["daily_ranking"]) == 12
    assert fortune["daily_ranking"][0]["rank"] == 1
    assert fortune["weekly"]
    assert fortune["monthly"]


def test_youtube_summary_generates_original_analysis_and_derivatives() -> None:
    result = YouTubeSummary().summarize(
        "https://youtube.com/watch?v=test",
        "AIで収益化するには発信が重要です。導線設計も必要です。改善を続けます。",
    )

    assert result["copyright_policy"].startswith("転載ではなく")
    assert result["ai_analysis"]
    assert result["note"]["body"]
    assert result["threads"]["text"]
    assert result["seo_article"]["title"]


def test_seo_lp_image_scheduler_analytics_and_ab_testing() -> None:
    lp = LandingPageBuilder().build("AIOS Content Factory")
    seo = SEOOptimizer().optimize(lp)
    image = ImagePromptBuilder().build(lp)
    schedule = ContentScheduler().schedule([lp], cadence="weekly")
    analytics = ContentAnalytics().summarize([{"estimated_revenue": 1000}], {"pv": 10, "ctr": 0.01, "cvr": 0.005, "revenue": 1000})
    ab = ABTesting().create(lp)

    assert seo["title"]
    assert seo["schema"]["@type"] == "Article"
    assert image["ogp_image"]
    assert schedule[0]["cadence"] == "weekly"
    assert analytics["improvement_candidates"]
    assert ab["winner"]
    assert ab["auto_adopt"] is True


def test_quality_reviewer_detects_short_or_risky_content() -> None:
    approved = QualityReviewer().review({"type": "note", "title": "AI収益化", "body": "AIOSでnote Threads affiliate SEO ROI 収益最大化を実行します。" * 3})
    risky = QualityReviewer().review({"type": "note", "body": "必ず儲かる"})

    assert approved["constitution_compliance"]["status"] == "compliant"
    assert risky["status"] == "needs_revision"
    assert "false_profit_claim" in risky["issues"]


def test_content_manager_daily_pack_persists_state_and_links_agents(tmp_path: Path, monkeypatch) -> None:
    manager = ContentFactoryManager(path=tmp_path / "content_factory.json")
    monkeypatch.setattr(manager, "send_to_business_engine", lambda contents, analytics: {"source": "business-test"})
    monkeypatch.setattr(manager, "send_to_revenue_engine", lambda contents, analytics: {"source": "revenue-test"})
    monkeypatch.setattr(manager, "send_to_coding_engine", lambda contents, analytics: {"source": "coding-test"})
    monkeypatch.setattr(manager, "save_knowledge", lambda contents, schedule, analytics, reviews: {"id": "knowledge-test"})

    run = manager.generate_daily_pack(topic="Threads占いで初収益")
    state = manager.load_state()

    assert len(run["contents"]) >= 6
    assert run["business_feedback"]["source"] == "business-test"
    assert run["revenue_feedback"]["source"] == "revenue-test"
    assert run["coding_feedback"]["source"] == "coding-test"
    assert state["knowledge_history"][0]["id"] == "knowledge-test"
    assert run["constitution_compliance"]["status"] == "compliant"


def test_content_manager_saves_knowledge_without_overwriting_existing(monkeypatch, tmp_path: Path) -> None:
    existing = {"success_examples": [{"id": "old"}], "failure_examples": [], "improvement_examples": [], "timeline": [], "categories": {}}
    saved = {}
    manager = ContentFactoryManager(path=tmp_path / "content_factory.json")

    monkeypatch.setattr("src.content_factory.content_manager.load_knowledge", lambda: existing)
    monkeypatch.setattr("src.content_factory.content_manager.save_knowledge", lambda data: saved.update(data))
    monkeypatch.setattr("src.content_factory.content_manager.record_improvement", lambda data: {"ok": True})

    record = manager.save_knowledge(
        [{"content_id": "c1", "estimated_revenue": 1000}],
        [{"schedule_id": "s1"}],
        {"revenue": 1000, "roi": 120},
        [{"status": "approved"}],
    )

    assert saved["success_examples"][0]["id"] == "old"
    assert saved["improvement_examples"][0]["id"] == record["id"]
    assert saved["categories"]["content_factory"] == 1


def test_next_content_prioritizes_ctr_or_cvr_improvement(tmp_path: Path) -> None:
    manager = ContentFactoryManager(path=tmp_path / "content_factory.json")

    next_low_ctr = manager.next_content([], {"ctr": 0.01, "cvr": 0.03})
    next_low_cvr = manager.next_content([], {"ctr": 0.08, "cvr": 0.01})

    assert next_low_ctr["type"] == "threads"
    assert next_low_cvr["type"] == "landing_page"


def test_content_engine_phase1_generates_queues_drafts_and_business_sync(tmp_path: Path) -> None:
    manager = ContentFactoryManager(path=tmp_path / "content_factory.json")
    manager.business_store = BusinessEngineStore(tmp_path / "business_engine.json")

    run = manager.generate_phase1_content(topic="AIOS初収益コンテンツ", category="revenue")
    state = manager.load_state()
    business = manager.business_store.load()

    assert run["phase"] == "Content Engine Phase1"
    assert run["dry_run"] is True
    assert run["local_first"] is True
    assert len(state["content_ideas"]) == 1
    assert len(state["content_queue"]) == 3
    assert {item["content_type"] for item in state["content_queue"]} == {"note", "threads", "official_site"}
    assert len(state["drafts"]) == 3
    assert all(Path(draft["path"]).exists() for draft in state["drafts"])
    assert state["history"][0]["event"] == "phase1_generated"
    assert any(item.get("type") == "official_site_article" for item in run["contents"])
    assert len(business["article_queue"]) == 1
    assert len([post for post in business["post_queue"] if post.get("platform") == "threads"]) == 1
    assert business["mission_planner_feedback"][0]["source"] == "content_engine_phase1"
    assert business["daily_kpis"][0]["note_articles"] == 1
    assert business["daily_kpis"][0]["threads_posts"] == 1


def test_content_engine_phase1_priority_follows_business_kpi(tmp_path: Path) -> None:
    manager = ContentFactoryManager(path=tmp_path / "content_factory.json")
    manager.business_store = BusinessEngineStore(tmp_path / "business_engine.json")
    manager.business_store.record_daily_kpi(
        revenue=0,
        articles=0,
        sns_posts=0,
        affiliate_clicks=0,
        pv=20,
        ctr=0.01,
    )

    idea = manager.add_content_idea("CTR改善", category="threads")
    note_queue = manager.queue_content(idea["idea_id"], "note")
    threads_queue = manager.queue_content(idea["idea_id"], "threads")
    official_queue = manager.queue_content(idea["idea_id"], "official_site")

    assert note_queue and note_queue["priority"] == "urgent"
    assert threads_queue and threads_queue["priority"] == "high"
    assert official_queue and official_queue["priority"] == "high"
