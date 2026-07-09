from __future__ import annotations

from pathlib import Path

from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.revenue_engine.market_analyzer import MarketAnalyzer
from src.revenue_engine.opportunity_engine import OpportunityEngine
from src.revenue_engine.revenue_planner import RevenuePlanner
from src.revenue_engine.roi_engine import ROIEngine


def test_revenue_score_is_100_point_scale_and_roi_first() -> None:
    engine = ROIEngine()
    high = engine.score(
        {
            "title": "Threads占い",
            "expected_revenue": 24000,
            "expected_profit": 22000,
            "estimated_cost": 2400,
            "effort_hours": 2,
            "difficulty": 25,
            "market_size": 80,
            "competition": 35,
            "continuity": 85,
            "automation_rate": 90,
            "risk": "low",
        }
    )
    low = engine.score(
        {
            "title": "低ROI作業",
            "expected_revenue": 4000,
            "expected_profit": 1000,
            "estimated_cost": 3000,
            "effort_hours": 8,
            "difficulty": 70,
            "market_size": 30,
            "competition": 80,
            "continuity": 30,
            "automation_rate": 20,
            "risk": "medium",
        }
    )

    assert 0 <= high["revenue_score"] <= 100
    assert high["revenue_score"] > low["revenue_score"]
    assert high["decision"] == "execute"


def test_opportunity_engine_generates_initial_revenue_candidates() -> None:
    opportunities = OpportunityEngine().generate()
    titles = [item["title"] for item in opportunities]

    assert "Threads占い" in titles
    assert "note記事" in titles
    assert "AIOS公式サイトSEO" in titles
    assert opportunities[0]["revenue_score"] >= opportunities[-1]["revenue_score"]
    assert all(item["constitution"]["illegal_gray_forbidden"] for item in opportunities)


def test_market_analyzer_adds_required_market_fields() -> None:
    result = MarketAnalyzer().analyze({"title": "AIツール紹介", "market_key": "ai_tool_intro"})

    analysis = result["market_analysis"]
    assert {"search_demand", "competition", "ad_cpc", "market_growth", "seasonality", "sns_buzz", "roi_estimate"}.issubset(analysis)
    assert result["market_size"] > 0


def test_revenue_planner_builds_today_week_month_quarter() -> None:
    ranked = OpportunityEngine().generate()
    plan = RevenuePlanner().build_plan(ranked)

    assert plan["today"]
    assert plan["week"]
    assert plan["month"]
    assert plan["quarter"]
    assert plan["mission_planner_payload"]["source"] == "revenue_engine"


def test_dashboard_run_cycle_persists_state_and_agent_payloads(tmp_path: Path, monkeypatch) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    business_feedback = [{"source": "business-test"}]
    coding_queue = [{"source": "coding-test"}]
    knowledge = {"id": "knowledge-test"}

    monkeypatch.setattr(dashboard, "send_to_business_engine", lambda ranked, plan, forecast: business_feedback)
    monkeypatch.setattr(dashboard, "send_to_coding_engine", lambda ranked: coding_queue)
    monkeypatch.setattr(dashboard, "save_knowledge", lambda ranked, plan, forecast: knowledge)

    run = dashboard.run_cycle()
    state = dashboard.load_state()

    assert run["top_action"]["title"]
    assert state["roi_ranking"]
    assert state["business_feedback"] == business_feedback
    assert state["coding_queue"] == coding_queue
    assert state["knowledge_history"][0] == knowledge
    assert run["constitution_compliance"]["status"] == "compliant"


def test_profit_forecast_and_channel_queues_are_generated(tmp_path: Path) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    ranked = OpportunityEngine().generate()

    forecast = dashboard.profit_forecast(ranked)
    queues = dashboard.channel_queues(ranked)

    assert forecast["weighted_profit"] > 0
    assert queues["threads"]
    assert queues["note"]
    assert queues["affiliate"]
    assert queues["seo"]


def test_knowledge_save_preserves_existing_buckets(tmp_path: Path, monkeypatch) -> None:
    ranked = OpportunityEngine().generate()
    plan = RevenuePlanner().build_plan(ranked)
    forecast = {"weighted_profit": 1000}
    loaded = {"success_examples": [{"id": "old"}], "failure_examples": [], "improvement_examples": [], "timeline": [], "categories": {}}
    saved = {}

    monkeypatch.setattr("src.revenue_engine.dashboard.load_knowledge", lambda: loaded)
    monkeypatch.setattr("src.revenue_engine.dashboard.save_knowledge", lambda data: saved.update(data))
    monkeypatch.setattr("src.revenue_engine.dashboard.record_improvement", lambda data: {"ok": True})

    record = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json").save_knowledge(ranked, plan, forecast)

    assert record["type"] == "revenue_engine"
    assert saved["success_examples"][0]["id"] == "old"
    assert saved["improvement_examples"][0]["id"] == record["id"]


def test_illegal_or_gray_opportunity_is_filtered() -> None:
    opportunities = OpportunityEngine().generate(
        [{"title": "違法グレー案件", "expected_revenue": 999999, "expected_profit": 999999, "risk": "low"}]
    )

    assert all("違法" not in item["title"] for item in opportunities)
