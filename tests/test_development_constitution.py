from __future__ import annotations

from copy import deepcopy

from src.business_engine.manager import BusinessEngineStore
from src.core import development_constitution as dc
from src.self_builder import agent_manager as am
from src.self_builder import continuous_engine as ce
from src.self_builder.knowledge_manager import load_knowledge


def test_constitution_load_and_persist_to_knowledge(tmp_path):
    constitution_path = tmp_path / "constitution.json"
    knowledge_path = tmp_path / "knowledge.json"

    constitution = dc.ensure_development_constitution(
        constitution_path=constitution_path,
        knowledge_path=knowledge_path,
    )
    knowledge = load_knowledge(knowledge_path)

    assert constitution["version"] == "1.0"
    assert constitution_path.exists()
    assert knowledge["development_constitution"]["version"] == "1.0"
    assert knowledge["history"][0]["type"] == "development_constitution"


def test_mission_planner_references_constitution_before_queue(monkeypatch):
    calls = {"ensure": 0}

    def ensure():
        calls["ensure"] += 1
        return {"version": "1.0", "priority_order": dc.PRIORITY_ORDER}

    monkeypatch.setattr(am, "ensure_development_constitution", ensure)
    monkeypatch.setattr("src.self_builder.knowledge_manager.memory_context", lambda instruction, plan: {"matched_count": 0, "matches": []})

    mission = am.mission_plan("note収益を改善して初収益へ近づける", "Pro Plan", ["src/business_engine/manager.py"])

    assert calls["ensure"] == 1
    assert mission["constitution"]["version"] == "1.0"
    assert mission["development_review"]["constitution_compliance"]["score"] >= 80
    assert all(item["constitution_reference"] == "Development Constitution v1.0" for item in mission["agent_queue"])


def test_review_agent_detects_constitution_violation():
    mission = {
        "agent_queue": [{"status": "done"}],
        "risk_level": "low",
        "instruction": "大型新機能を目的不明で追加する",
        "development_review": {
            "purpose": "コード増加",
            "completion_conditions": [],
            "large_feature_suppressed": True,
        },
    }

    review = am.final_review(mission)

    assert review["status"] == "needs_attention"
    assert "Constitution準拠" in review["missing"]
    assert review["constitution_compliance"]["status"] == "violation"


def test_business_engine_scores_roi_and_revenue_contribution(tmp_path, monkeypatch):
    records = []
    monkeypatch.setattr("src.business_engine.manager.record_improvement", lambda improvement: records.append(deepcopy(improvement)) or improvement)

    store = BusinessEngineStore(tmp_path / "business.json")
    store.record_daily_kpi(revenue=12000, articles=2, sns_posts=3, pv=1000, ctr=0.08)

    evaluation = store.evaluate_improvement_roi(
        {
            "instruction": "noteとThreadsの収益導線を改善する",
            "estimated_revenue": 30000,
            "risk": "low",
            "effort": 15,
        }
    )

    assert evaluation["decision"] == "prioritize"
    assert evaluation["business_metrics"]["pv"] == 1000
    assert evaluation["score"]["constitution_priority_score"] > 0
    assert records


def test_continuous_priority_uses_roi_risk_effort_profitability():
    history = [
        {
            "status": "approved",
            "created_at": "2026-07-08T00:00:00",
            "run": {
                "run_id": "low-value",
                "candidate": {"instruction": "小さいUI調整", "estimated_revenue": 1000, "estimated_minutes_saved": 1, "risk": "low", "effort": 5},
            },
        },
        {
            "status": "approved",
            "created_at": "2026-07-08T00:00:00",
            "run": {
                "run_id": "revenue-first",
                "candidate": {"instruction": "note収益とSEO改善", "estimated_revenue": 40000, "estimated_minutes_saved": 5, "risk": "low", "effort": 10},
            },
        },
    ]

    ranking = ce._improvement_ranking(history)

    assert ranking[0]["run_id"] == "revenue-first"
    assert ranking[0]["constitution_priority_score"] >= ranking[1]["constitution_priority_score"]


def test_settings_ui_contains_development_constitution_tab():
    text = (dc.PROJECT_ROOT / "pages" / "9_Settings.py").read_text(encoding="utf-8")

    assert "Development Constitution" in text
    assert "Violation History" in text
    assert "ROI Impact" in text
