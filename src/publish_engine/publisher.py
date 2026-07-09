from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.business_engine.manager import BusinessEngineStore
from src.core.development_constitution import development_review, evaluate_constitution_compliance, record_improvement
from src.publish_engine.analytics_sync import AnalyticsSync
from src.publish_engine.approval_manager import ApprovalManager
from src.publish_engine.manual_publisher import ManualPublisher, build_note_text, build_threads_text
from src.publish_engine.note_publisher import NotePublisher
from src.publish_engine.oauth_manager import OAuthManager
from src.publish_engine.publish_logger import PublishLogger
from src.publish_engine.publish_queue import PublishQueue
from src.publish_engine.retry_manager import RetryManager
from src.publish_engine.rollback_manager import RollbackManager
from src.publish_engine.rss_manager import RSSManager
from src.publish_engine.scheduler import PublishScheduler
from src.publish_engine.threads_publisher import ThreadsPublisher
from src.publish_engine.wordpress_publisher import WordPressPublisher
from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic


PUBLISH_ENGINE_PATH = PROJECT_ROOT / "config" / "publish_engine.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "publish_mode": "manual",
        "dry_run_default": True,
        "queue": [],
        "schedule": [],
        "history": [],
        "analytics": [],
        "retries": [],
        "rollbacks": [],
        "logs": [],
        "knowledge_history": [],
        "last_run": {},
        "updated_at": _now(),
    }


class PublishEngine:
    def __init__(self, path: str | Path = PUBLISH_ENGINE_PATH, *, revenue_dashboard: RevenueEngineDashboard | None = None) -> None:
        self.path = Path(path)
        self.queue = PublishQueue()
        self.approval = ApprovalManager()
        self.oauth = OAuthManager()
        self.scheduler = PublishScheduler()
        self.analytics = AnalyticsSync()
        self.retry = RetryManager()
        self.rollback = RollbackManager()
        self.logger = PublishLogger()
        self.business_store = BusinessEngineStore()
        self.revenue_dashboard = revenue_dashboard or RevenueEngineDashboard()

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

    def create_draft(self, content: dict[str, Any], platform: str, *, priority: int = 50) -> dict[str, Any]:
        state = self.load_state()
        item = self.queue.create_item(content, platform, priority=priority)
        item["review"] = self.approval.review(item)
        item["status"] = "review"
        self.queue.add(state, item)
        state.setdefault("logs", []).insert(0, self.logger.entry(item, "draft_created", {"review": item["review"]}))
        self.save_state(state)
        return item

    def set_dry_run(self, enabled: bool = True) -> dict[str, Any]:
        state = self.load_state()
        state["dry_run_default"] = bool(enabled)
        state.setdefault("logs", []).insert(0, {"event": "dry_run_changed", "enabled": bool(enabled), "created_at": _now()})
        self.save_state(state)
        return {"dry_run_default": state["dry_run_default"]}

    def set_publish_mode(self, mode: str = "manual") -> dict[str, Any]:
        state = self.load_state()
        normalized = "api" if mode == "api" else "manual"
        state["publish_mode"] = normalized
        state.setdefault("logs", []).insert(0, {"event": "publish_mode_changed", "mode": normalized, "created_at": _now()})
        self.save_state(state)
        return {"publish_mode": normalized}

    def create_manual_pack(self, content: dict[str, Any], *, priority: int = 50) -> list[dict[str, Any]]:
        threads = dict(content)
        threads["text"] = build_threads_text(content)
        note = dict(content)
        note["body"] = build_note_text(content)
        return [
            self.create_draft({**threads, "type": "threads"}, "threads", priority=priority),
            self.create_draft({**note, "type": "note"}, "note", priority=priority),
        ]

    def approve(self, publish_id: str, reviewer: str = "AIOS") -> dict[str, Any] | None:
        state = self.load_state()
        item = self.queue.update(state, publish_id, status="approved", approval=self.approval.approve({"publish_id": publish_id}, reviewer))
        if item:
            state.setdefault("logs", []).insert(0, self.logger.entry(item, "approved"))
            self.save_state(state)
        return item

    def schedule(self, publish_id: str, *, days_from_now: int = 0) -> dict[str, Any] | None:
        state = self.load_state()
        item = next((row for row in state.get("queue", []) if row.get("publish_id") == publish_id), None)
        if item is None:
            return None
        scheduled = self.scheduler.schedule(item, days_from_now=days_from_now)
        item.update(scheduled)
        state.setdefault("schedule", []).insert(0, scheduled)
        state.setdefault("logs", []).insert(0, self.logger.entry(item, "scheduled", {"scheduled_for": item.get("scheduled_for")}))
        self.save_state(state)
        return item

    def publish_next(self) -> dict[str, Any]:
        state = self.load_state()
        item = self.queue.next_ready(state)
        if item is None:
            return {"status": "empty", "message": "No approved publish item."}
        return self.publish(item.get("publish_id", ""))

    def run_queue(self, *, limit: int | None = None) -> dict[str, Any]:
        results = []
        while limit is None or len(results) < limit:
            result = self.publish_next()
            if result.get("status") == "empty":
                break
            results.append(result)
        return {
            "status": "completed",
            "processed": len(results),
            "success": len([row for row in results if row.get("status") in {"published", "dry_run", "manual_ready", "posted"}]),
            "failed": len([row for row in results if row.get("status") not in {"published", "dry_run", "manual_ready", "posted"}]),
            "results": results,
        }

    def publish(self, publish_id: str) -> dict[str, Any]:
        state = self.load_state()
        item = next((row for row in state.get("queue", []) if row.get("publish_id") == publish_id), None)
        if item is None:
            return {"status": "missing", "publish_id": publish_id}
        review = item.get("review") or self.approval.review(item)
        if item.get("status") not in {"approved", "scheduled", "retry"} or review.get("status") != "approved":
            item["status"] = "rejected"
            item["review"] = review
            rollback = self.rollback.create_plan(item, "approval_required")
            state.setdefault("rollbacks", []).insert(0, rollback)
            state.setdefault("logs", []).insert(0, self.logger.entry(item, "rejected", {"reason": "approval_required", "review": review}))
            self.save_state(state)
            return {"status": "rejected", "reason": "approval_required", "review": review, "rollback": rollback}
        publish_mode = str(state.get("publish_mode", "manual") or "manual")
        oauth = self.oauth.status(str(item.get("platform", "")))
        dry_run = bool(state.get("dry_run_default", True) or (publish_mode != "manual" and oauth.get("dry_run", True)))
        try:
            result = self._publisher_for(item.get("platform", "")).publish(item, dry_run=dry_run)
        except Exception as exc:
            retry = self.retry.queue_retry(item, str(exc))
            rollback = self.rollback.create_plan(item, str(exc))
            item["status"] = retry["status"]
            item["attempts"] = retry["attempts"]
            state.setdefault("retries", []).insert(0, retry)
            state.setdefault("rollbacks", []).insert(0, rollback)
            self.save_state(state)
            return {"status": "failed", "retry": retry, "rollback": rollback}

        item["publish_result"] = result
        if not self._publish_success(result):
            rollback = self.rollback.create_plan(item, str(result.get("message") or result.get("error") or result.get("status", "failed")))
            item["status"] = "failed"
            state.setdefault("rollbacks", []).insert(0, rollback)
            state.setdefault("logs", []).insert(0, self.logger.entry(item, "failed", result))
            self.save_state(state)
            return {"status": "failed", "result": result, "rollback": rollback}

        item["status"] = result.get("status", "published")
        item["attempts"] = int(item.get("attempts", 0)) + 1
        metrics = self.analytics.sync(item)
        item["analytics"] = metrics
        state.setdefault("analytics", []).insert(0, metrics)
        state.setdefault("history", []).insert(0, dict(item))
        state["history"] = state["history"][:300]
        state.setdefault("logs", []).insert(0, self.logger.entry(item, "published", result))
        knowledge = self.save_knowledge(item, metrics)
        dashboard = self.record_dashboard_publish(item, metrics, result)
        revenue = self.feedback_revenue(item, metrics)
        business = self.feedback_business(item, metrics)
        coding = self.feedback_coding(item, metrics)
        compliance = evaluate_constitution_compliance(
            {
                "instruction": "Publish Engine公開前レビュー APIキー保護 Knowledge保存 Rollback Retry Revenue ROI",
                "development_review": development_review({"instruction": "公開前レビュー 収益 ROI Knowledge Publish Engine"}),
                "publish_result": result,
            }
        )
        run = {
            "status": item["status"],
            "publish_id": item.get("publish_id", ""),
            "result": result,
            "analytics": metrics,
            "dashboard_record": dashboard,
            "knowledge_record": knowledge,
            "revenue_feedback": revenue,
            "business_feedback": business,
            "coding_feedback": coding,
            "constitution_compliance": compliance,
        }
        state.setdefault("knowledge_history", []).insert(0, knowledge)
        state["last_run"] = run
        self.save_state(state)
        return run

    def mark_posted(self, publish_id: str, *, posted_url: str = "", reviewer: str = "AIOS") -> dict[str, Any]:
        state = self.load_state()
        item = next((row for row in state.get("queue", []) if row.get("publish_id") == publish_id), None)
        if item is None:
            item = next((row for row in state.get("history", []) if row.get("publish_id") == publish_id), None)
        if item is None:
            return {"status": "missing", "publish_id": publish_id}
        item["status"] = "posted"
        item["posted"] = True
        item["posted_url"] = posted_url
        item["posted_at"] = _now()
        item["posted_by"] = reviewer
        item.setdefault("publish_result", {})
        item["publish_result"].update(
            {
                "status": "posted",
                "manual_mode": True,
                "posted": True,
                "posted_url": posted_url,
                "posted_at": item["posted_at"],
            }
        )
        state.setdefault("history", []).insert(0, dict(item))
        state["history"] = state["history"][:300]
        state.setdefault("logs", []).insert(0, self.logger.entry(item, "manual_posted", {"posted_url": posted_url}))
        state["last_run"] = {"status": "posted", "publish_id": publish_id, "posted_url": posted_url}
        self.save_state(state)
        return {"status": "posted", "publish_id": publish_id, "posted_url": posted_url}

    def record_dashboard_publish(self, item: dict[str, Any], metrics: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        return self.revenue_dashboard.record_publish_history(
            {
                "publish_id": item.get("publish_id", ""),
                "platform": item.get("platform", ""),
                "status": item.get("status", ""),
                "content_id": item.get("content_id", ""),
                "title": item.get("content", {}).get("title", ""),
                "dry_run": bool(result.get("dry_run", False)),
                "external_id": result.get("external_id", ""),
                "metrics": metrics,
                "created_at": _now(),
            }
        )

    def save_knowledge(self, item: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
        knowledge = load_knowledge()
        record = {
            "id": f"pk-{item.get('publish_id', '')}",
            "type": "publish_engine",
            "platform": item.get("platform", ""),
            "status": item.get("status", ""),
            "content_id": item.get("content_id", ""),
            "metrics": metrics,
            "created_at": _now(),
        }
        bucket = "success_examples" if item.get("status") in {"published", "dry_run", "manual_ready", "posted"} else "failure_examples"
        knowledge.setdefault(bucket, []).insert(0, record)
        knowledge.setdefault("timeline", []).insert(0, record)
        knowledge.setdefault("categories", {}).setdefault("publish_engine", 0)
        knowledge["categories"]["publish_engine"] += 1
        save_knowledge(knowledge)
        record_improvement(
            {
                "instruction": "Publish Engine analytics feedback",
                "estimated_revenue": metrics.get("revenue", 0),
                "estimated_cost": 500,
                "risk": "low" if item.get("status") == "dry_run" else "medium",
            }
        )
        return record

    def feedback_revenue(self, item: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
        try:
            run = RevenueEngineDashboard().run_cycle(
                extra_candidates=[
                    {
                        "title": f"Published content: {item.get('platform')}",
                        "channel": item.get("platform", ""),
                        "expected_revenue": metrics.get("revenue", 0),
                        "expected_profit": int(metrics.get("revenue", 0) * 0.8),
                        "effort_hours": 0.5,
                        "difficulty": 20,
                        "risk": "low",
                        "continuity": 75,
                        "automation_rate": 85,
                        "next_action": "公開結果の勝ちパターンを横展開",
                    }
                ]
            )
            return {"source": "publish_engine", "revenue_run_id": run.get("run_id", "")}
        except Exception as exc:
            return {"source": "publish_engine", "error": str(exc)}

    def feedback_business(self, item: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
        data = self.business_store.load()
        feedback = {"source": "publish_engine", "publish_id": item.get("publish_id", ""), "metrics": metrics, "created_at": _now()}
        data.setdefault("mission_planner_feedback", []).insert(0, feedback)
        data["mission_planner_feedback"] = data["mission_planner_feedback"][:100]
        self.business_store.save(data)
        self.business_store.record_daily_kpi(
            revenue=int(metrics.get("revenue", 0)),
            pv=int(metrics.get("pv", 0)),
            ctr=float(metrics.get("ctr", 0)),
            cv=float(metrics.get("cvr", 0)),
            roi=int(metrics.get("roi", 0)),
            notes="Publish Engine analytics sync",
        )
        return feedback

    def feedback_coding(self, item: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
        queue = [
            {
                "source": "publish_engine",
                "priority": int(metrics.get("roi", 0)),
                "instruction": "公開成功率・分析同期・Rollback/Retryを改善",
                "target_hint": "src/publish_engine/",
                "created_at": _now(),
            }
        ]
        path = PROJECT_ROOT / "config" / "coding_engine.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception:
            data = {}
        data.setdefault("publish_improvement_queue", [])
        data["publish_improvement_queue"] = queue + data["publish_improvement_queue"]
        data["publish_improvement_queue"] = data["publish_improvement_queue"][:100]
        save_json_atomic(path, data)
        return {"source": "publish_engine", "queue": queue}

    def dashboard_summary(self) -> dict[str, Any]:
        state = self.load_state()
        history = state.get("history", [])
        success = [item for item in history if item.get("status") in {"published", "dry_run", "manual_ready", "posted"}]
        errors = [item for item in history if item.get("status") in {"failed", "rejected"}]
        revenue = sum(int(item.get("analytics", {}).get("revenue", 0)) for item in history)
        roi = int(sum(int(item.get("analytics", {}).get("roi", 0)) for item in history) / max(len(history), 1))
        return {
            "waiting": len([item for item in state.get("queue", []) if item.get("status") in {"draft", "review", "approved", "scheduled"}]),
            "today_scheduled": len(state.get("schedule", [])),
            "success_rate": round(len(success) / max(len(history), 1) * 100, 1),
            "errors": len(errors),
            "revenue": revenue,
            "roi": roi,
            "history_count": len(history),
        }

    def _publisher_for(self, platform: str) -> Any:
        if self.load_state().get("publish_mode", "manual") == "manual" and platform in {"threads", "note"}:
            return ManualPublisher()
        return {
            "threads": ThreadsPublisher(),
            "note": NotePublisher(),
            "wordpress": WordPressPublisher(),
            "rss": __import__("src.publish_engine.rss_manager", fromlist=["RSSManager"]).RSSManager(),
        }.get(platform, RSSManager())

    @staticmethod
    def _publish_success(result: dict[str, Any]) -> bool:
        return result.get("status") in {"published", "dry_run", "manual_ready", "posted"}
