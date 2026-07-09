from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.business_engine.manager import BusinessEngineStore
from src.core.development_constitution import development_review, evaluate_constitution_compliance, record_improvement
from src.revenue_engine.affiliate_manager import AffiliateManager
from src.revenue_engine.note_manager import NoteManager
from src.revenue_engine.opportunity_engine import OpportunityEngine
from src.revenue_engine.revenue_planner import RevenuePlanner
from src.revenue_engine.seo_manager import SEOManager
from src.revenue_engine.threads_manager import ThreadsManager
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic


REVENUE_ENGINE_PATH = PROJECT_ROOT / "config" / "revenue_engine.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "mission": "revenue_maximization",
        "constitution": {
            "revenue_maximization": True,
            "roi_first": True,
            "long_term_profit": True,
            "illegal_gray_forbidden": True,
            "auto_improvement_required": True,
            "knowledge_required": True,
            "agent_integration_required": True,
        },
        "opportunities": [],
        "roi_ranking": [],
        "plans": {},
        "business_feedback": [],
        "coding_queue": [],
        "knowledge_history": [],
        "note_draft_saves": [],
        "threads_waiting_posts": [],
        "publish_approval_candidates": [],
        "publish_approval_history": [],
        "publish_history": [],
        "forecasts": {},
        "last_run": {},
        "updated_at": _now(),
    }


class RevenueEngineDashboard:
    def __init__(self, path: str | Path = REVENUE_ENGINE_PATH) -> None:
        self.path = Path(path)
        self.opportunities = OpportunityEngine()
        self.planner = RevenuePlanner()
        self.business_store = BusinessEngineStore()

    def load_state(self) -> dict[str, Any]:
        if not self.path.exists():
            state = _default_state()
            self.save_state(state)
            return state
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            data = _default_state()
        if not isinstance(data, dict):
            data = _default_state()
        defaults = _default_state()
        for key, value in defaults.items():
            data.setdefault(key, value)
        return data

    def save_state(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = _now()
        save_json_atomic(self.path, state)

    def record_note_draft_save(self, record: dict[str, Any]) -> dict[str, Any]:
        state = self.load_state()
        saved = {**record, "recorded_at": _now()}
        state.setdefault("note_draft_saves", []).insert(0, saved)
        state["note_draft_saves"] = state["note_draft_saves"][:100]
        state["last_note_draft_save"] = saved
        self.save_state(state)
        return saved

    def record_threads_waiting_post(self, record: dict[str, Any]) -> dict[str, Any]:
        state = self.load_state()
        waiting = {**record, "status": "waiting", "dry_run": True, "recorded_at": _now()}
        state.setdefault("threads_waiting_posts", []).insert(0, waiting)
        state["threads_waiting_posts"] = state["threads_waiting_posts"][:100]
        state["last_threads_waiting_post"] = waiting
        self.save_state(state)
        return waiting

    def record_publish_history(self, record: dict[str, Any]) -> dict[str, Any]:
        state = self.load_state()
        saved = {**record, "recorded_at": _now()}
        state.setdefault("publish_history", []).insert(0, saved)
        state["publish_history"] = state["publish_history"][:100]
        state["last_publish_history"] = saved
        self.save_state(state)
        return saved

    def run_cycle(self, extra_candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        ranked = self.opportunities.generate(extra_candidates)
        plan = self.planner.build_plan(ranked)
        forecast = self.profit_forecast(ranked)
        business_feedback = self.send_to_business_engine(ranked, plan, forecast)
        coding_queue = self.send_to_coding_engine(ranked)
        knowledge_record = self.save_knowledge(ranked, plan, forecast)
        channel_queues = self.channel_queues(ranked)
        compliance = evaluate_constitution_compliance(
            {
                "instruction": "Revenue Engine maximizes profit by ROI-first autonomous actions.",
                "development_review": development_review({"instruction": "収益最大化 ROI 初収益 Business Engine note Threads affiliate SEO"}),
                "opportunities": ranked[:3],
            }
        )
        run = {
            "run_id": f"rev-{uuid4().hex[:10]}",
            "created_at": _now(),
            "top_action": ranked[0] if ranked else {},
            "opportunity_count": len(ranked),
            "forecast": forecast,
            "business_feedback": business_feedback,
            "coding_queue": coding_queue,
            "knowledge_record": knowledge_record,
            "constitution_compliance": compliance,
            "channel_queues": channel_queues,
        }
        state = self.load_state()
        state["opportunities"] = ranked
        state["roi_ranking"] = ranked
        state["plans"] = plan
        state["forecasts"] = forecast
        state["business_feedback"] = business_feedback
        state["coding_queue"] = coding_queue
        state.setdefault("knowledge_history", []).insert(0, knowledge_record)
        state["knowledge_history"] = state["knowledge_history"][:100]
        state["last_run"] = run
        self.save_state(state)
        return run

    def profit_forecast(self, ranked: list[dict[str, Any]]) -> dict[str, Any]:
        today = sum(int(item.get("expected_profit", 0)) for item in ranked[:1])
        week = sum(int(item.get("expected_profit", 0)) for item in ranked[:3])
        month = sum(int(item.get("expected_profit", 0)) for item in ranked[:5])
        quarter = sum(int(item.get("expected_profit", 0)) for item in ranked[:8])
        weighted = sum(int(item.get("expected_profit", 0)) * int(item.get("revenue_score", 0)) / 100 for item in ranked[:8])
        return {
            "today_profit": int(today),
            "week_profit": int(week),
            "month_profit": int(month),
            "quarter_profit": int(quarter),
            "weighted_profit": int(weighted),
            "generated_at": _now(),
        }

    def send_to_business_engine(
        self,
        ranked: list[dict[str, Any]],
        plan: dict[str, Any],
        forecast: dict[str, Any],
    ) -> list[dict[str, Any]]:
        feedback = []
        for item in ranked[:8]:
            evaluation = self.business_store.evaluate_improvement_roi(
                {
                    "instruction": item.get("title", ""),
                    "estimated_revenue": item.get("expected_revenue", 0),
                    "estimated_cost": item.get("estimated_cost", 0),
                    "estimated_effort": int(float(item.get("effort_hours", 1)) * 60),
                    "risk": item.get("risk", "medium"),
                    "profit": item.get("expected_profit", 0),
                    "roi": item.get("roi", 0),
                }
            )
            feedback.append(
                {
                    "source": "revenue_engine",
                    "opportunity_id": item.get("opportunity_id", ""),
                    "title": item.get("title", ""),
                    "revenue_score": item.get("revenue_score", 0),
                    "decision": item.get("decision", ""),
                    "business_evaluation": evaluation,
                }
            )
        data = self.business_store.load()
        data.setdefault("mission_planner_feedback", []).insert(0, plan["mission_planner_payload"])
        data["mission_planner_feedback"] = data["mission_planner_feedback"][:100]
        data.setdefault("revenue_engine_feedback", []).insert(
            0,
            {
                "date": date.today().isoformat(),
                "forecast": forecast,
                "top_opportunity": ranked[0] if ranked else {},
                "feedback": feedback,
                "created_at": _now(),
            },
        )
        data["revenue_engine_feedback"] = data["revenue_engine_feedback"][:100]
        self.business_store.save(data)
        if ranked:
            self.business_store.record_daily_kpi(
                revenue=int(forecast.get("weighted_profit", 0)),
                articles=len([item for item in ranked if item.get("channel") == "note"]),
                sns_posts=len([item for item in ranked if item.get("channel") == "threads"]),
                affiliate_clicks=len([item for item in ranked if item.get("channel") == "affiliate"]),
                roi=int(ranked[0].get("roi", 0)),
                notes="Revenue Engine forecast",
            )
        return feedback

    def send_to_coding_engine(self, ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        queue = []
        for item in ranked[:5]:
            queue.append(
                {
                    "queue_id": f"rcq-{uuid4().hex[:10]}",
                    "source": "revenue_engine",
                    "priority": item.get("revenue_score", 0),
                    "instruction": f"収益改善: {item.get('title')} - {item.get('next_action')}",
                    "expected_profit": item.get("expected_profit", 0),
                    "risk": item.get("risk", "medium"),
                    "target_hint": self._target_hint(item),
                    "created_at": _now(),
                }
            )
        coding_path = PROJECT_ROOT / "config" / "coding_engine.json"
        try:
            data = json.loads(coding_path.read_text(encoding="utf-8")) if coding_path.exists() else {}
        except Exception:
            data = {}
        data.setdefault("revenue_improvement_queue", [])
        data["revenue_improvement_queue"] = queue + data["revenue_improvement_queue"]
        data["revenue_improvement_queue"] = data["revenue_improvement_queue"][:100]
        save_json_atomic(coding_path, data)
        return queue

    def save_knowledge(
        self,
        ranked: list[dict[str, Any]],
        plan: dict[str, Any],
        forecast: dict[str, Any],
        *,
        outcome: str = "planned",
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        knowledge = load_knowledge()
        record = {
            "id": f"revk-{uuid4().hex[:10]}",
            "type": "revenue_engine",
            "outcome": outcome,
            "top_action": ranked[0] if ranked else {},
            "plan": plan,
            "forecast": forecast,
            "metrics": {
                "ctr": 0,
                "cvr": 0,
                "profit": forecast.get("weighted_profit", 0),
                "roi": ranked[0].get("roi", 0) if ranked else 0,
                **(metrics or {}),
            },
            "created_at": _now(),
        }
        bucket = "success_examples" if outcome == "success" else "failure_examples" if outcome == "failure" else "improvement_examples"
        knowledge.setdefault(bucket, []).insert(0, record)
        knowledge.setdefault("timeline", []).insert(0, record)
        knowledge.setdefault("categories", {}).setdefault("revenue_engine", 0)
        knowledge["categories"]["revenue_engine"] += 1
        save_knowledge(knowledge)
        record_improvement(
            {
                "instruction": "Revenue Engine ROI planning",
                "estimated_revenue": forecast.get("weighted_profit", 0),
                "estimated_cost": ranked[0].get("estimated_cost", 1000) if ranked else 1000,
                "risk": ranked[0].get("risk", "medium") if ranked else "medium",
            }
        )
        return record

    def channel_queues(self, ranked: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "affiliate": AffiliateManager().queue(ranked),
            "note": NoteManager().queue(ranked),
            "threads": ThreadsManager().queue(ranked),
            "seo": SEOManager().queue(ranked),
        }

    @staticmethod
    def _target_hint(item: dict[str, Any]) -> str:
        channel = item.get("channel")
        return {
            "threads": "src/business_engine/threads_automation.py",
            "note": "src/factories/note/",
            "official_site": "src/official_site/",
            "affiliate": "src/business_engine/manager.py",
        }.get(channel, "src/revenue_engine/")
