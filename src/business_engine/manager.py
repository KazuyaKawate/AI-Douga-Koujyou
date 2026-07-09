from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.approval.approval_queue import content_review_summary
from src.business_engine.adapters import AdapterRegistry, default_adapter_state
from src.core.development_constitution import record_improvement, score_improvement
from src.creator_factory.factory_manager import creator_factory_summary
from src.export.export_manager import export_summary
from src.providers.provider_registry import get_provider_registry
from src.utils.json_store import load_json, save_json_atomic

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "config" / "business_engine.json"

REVENUE_STAGES = ["idea", "queued", "in_progress", "published", "monetizing", "earned", "lost"]
GEMINI_RUNTIME_JOB_TYPES = [
    "gemini_note_article",
    "gemini_sns_post",
    "gemini_seo_article",
    "gemini_affiliate_description",
    "gemini_business_report",
]
JOB_TYPES = ["note_article", "sns_post", "affiliate_publish", *GEMINI_RUNTIME_JOB_TYPES]
LEGACY_JOB_TYPE_ALIASES = {
    "sns_schedule": "sns_post",
    "affiliate_queue": "affiliate_publish",
}
JOB_STATUSES = ["queued", "running", "completed", "failed", "retry_queued"]

STAGE_PROBABILITY = {
    "idea": 10,
    "queued": 20,
    "in_progress": 35,
    "published": 50,
    "monetizing": 70,
    "earned": 100,
    "lost": 0,
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _job_template(job_type: str, title: str, due_date: str) -> dict[str, Any]:
    return {
        "job_id": _new_id("job"),
        "job_type": job_type,
        "title": title,
        "status": "queued",
        "due_date": due_date,
        "priority": "normal",
        "payload": {},
        "attempts": 0,
        "max_attempts": 3,
        "last_error": "",
        "created_at": _now(),
        "updated_at": _now(),
    }


def _default_scheduler_state() -> dict[str, Any]:
    return {
        "enabled": False,
        "status": "stopped",
        "interval_seconds": 300,
        "heartbeat_at": "",
        "last_tick_at": "",
        "last_result": "Scheduler disabled by default.",
    }


def _default_ai_runtime_state() -> dict[str, Any]:
    return {
        "provider": "gemini_cli",
        "prompt_queue": [],
        "runtime_logs": [],
        "last_provider_call": "",
        "last_runtime_ms": 0,
        "last_tokens": 0,
        "estimated_cost_yen": 0,
    }


def default_store() -> dict[str, Any]:
    today = date.today().isoformat()
    return {
        "meta": {
            "version": "5.2-business-phase4",
            "created_at": _now(),
            "local_first": True,
            "external_apis_enabled": False,
        },
        "scheduler_daemon": _default_scheduler_state(),
        "ai_runtime": _default_ai_runtime_state(),
        "adapters": default_adapter_state(),
        "revenue_pipeline": [],
        "scheduled_jobs": [
            _job_template("note_article", "Daily note article draft", today),
            _job_template("sns_post", "Daily SNS scheduling", today),
            _job_template("affiliate_publish", "Affiliate queue review", today),
        ],
        "daily_kpis": [],
        "execution_history": [],
        "retry_queue": [],
        "article_queue": [],
        "note_reservations": [],
        "posting_history": [],
        "post_queue": [],
        "threads_reservations": [],
        "threads_history": [],
        "threads_improvements": [],
        "affiliate_queue": [],
        "seo_queue": [],
        "content_automation_runs": [],
        "research_feedback": [],
        "mission_planner_feedback": [],
        "constitution_business_evaluations": [],
        "worker": {
            "status": "idle",
            "current_job_id": "",
            "current_job_title": "",
            "last_run_at": "",
            "last_message": "",
        },
    }


class BusinessEngineStore:
    """JSON-backed local Business Engine state store."""

    def __init__(self, path: str | Path = DEFAULT_PATH) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        data = load_json(self.path, default=None)
        if not isinstance(data, dict):
            data = default_store()
            self.save(data)
        defaults = default_store()
        for key, value in defaults.items():
            data.setdefault(key, value)
        data.setdefault("ai_runtime", {})
        for key, value in _default_ai_runtime_state().items():
            data["ai_runtime"].setdefault(key, value)
        data.setdefault("meta", {})
        data["meta"].setdefault("local_first", True)
        data["meta"].setdefault("external_apis_enabled", False)
        return data

    def save(self, data: dict[str, Any]) -> Path:
        data.setdefault("meta", {})
        data["meta"]["updated_at"] = _now()
        return save_json_atomic(self.path, data)

    def add_revenue_item(
        self,
        title: str,
        channel: str = "note",
        expected_revenue: int = 0,
        stage: str = "idea",
        due_date: str = "",
        probability: int | None = None,
        memo: str = "",
    ) -> dict[str, Any]:
        if stage not in REVENUE_STAGES:
            stage = "idea"
        item = {
            "item_id": _new_id("rev"),
            "title": title,
            "channel": channel,
            "stage": stage,
            "expected_revenue": int(expected_revenue or 0),
            "probability": int(probability if probability is not None else STAGE_PROBABILITY[stage]),
            "due_date": due_date,
            "memo": memo,
            "created_at": _now(),
            "updated_at": _now(),
        }
        data = self.load()
        data["revenue_pipeline"].insert(0, item)
        self.save(data)
        return item

    def update_revenue_stage(self, item_id: str, stage: str) -> dict[str, Any] | None:
        if stage not in REVENUE_STAGES:
            return None
        data = self.load()
        for item in data["revenue_pipeline"]:
            if item.get("item_id") == item_id:
                item["stage"] = stage
                item["probability"] = STAGE_PROBABILITY[stage]
                item["updated_at"] = _now()
                self.save(data)
                return item
        return None

    def pipeline_summary(self) -> dict[str, Any]:
        items = self.load().get("revenue_pipeline", [])
        open_items = [i for i in items if i.get("stage") not in ("earned", "lost")]
        earned_items = [i for i in items if i.get("stage") == "earned"]
        expected = sum(int(i.get("expected_revenue", 0)) for i in open_items)
        weighted = sum(
            int(i.get("expected_revenue", 0)) * int(i.get("probability", 0)) / 100
            for i in open_items
        )
        earned = sum(int(i.get("expected_revenue", 0)) for i in earned_items)
        return {
            "total_items": len(items),
            "open_items": len(open_items),
            "earned_items": len(earned_items),
            "expected_revenue": int(expected),
            "weighted_forecast": int(weighted),
            "earned_revenue": int(earned),
        }

    def schedule_job(
        self,
        job_type: str,
        title: str,
        due_date: str | None = None,
        priority: str = "normal",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        job_type = normalize_job_type(job_type)
        if job_type not in JOB_TYPES:
            raise ValueError(f"Unsupported job_type: {job_type}")
        job = _job_template(job_type, title, due_date or date.today().isoformat())
        job["priority"] = priority
        job["payload"] = payload or {}
        data = self.load()
        data["scheduled_jobs"].insert(0, job)
        self.save(data)
        return job

    def update_job_status(self, job_id: str, status: str, error: str = "") -> dict[str, Any] | None:
        if status not in JOB_STATUSES:
            return None
        data = self.load()
        for job in data["scheduled_jobs"]:
            if job.get("job_id") == job_id:
                job["status"] = status
                job["updated_at"] = _now()
                if error:
                    job["last_error"] = error
                if status == "running":
                    job["attempts"] = int(job.get("attempts", 0)) + 1
                if status == "failed":
                    self._queue_retry(data, job, error)
                self.save(data)
                return job
        return None

    def set_worker_state(
        self,
        status: str,
        *,
        current_job_id: str = "",
        current_job_title: str = "",
        message: str = "",
    ) -> dict[str, Any]:
        data = self.load()
        worker = data.setdefault("worker", {})
        worker.update({
            "status": status,
            "current_job_id": current_job_id,
            "current_job_title": current_job_title,
            "last_run_at": _now(),
            "last_message": message,
        })
        self.save(data)
        return worker

    def execution_monitor(self) -> dict[str, Any]:
        data = self.load()
        jobs = data.get("scheduled_jobs", [])
        today = date.today().isoformat()
        completed_today = sum(
            1 for j in jobs
            if j.get("status") == "completed" and str(j.get("updated_at", "")).startswith(today)
        )
        failed_today = sum(
            1 for j in jobs
            if j.get("status") == "failed" and str(j.get("updated_at", "")).startswith(today)
        )
        by_status = {status: 0 for status in JOB_STATUSES}
        for job in jobs:
            status = job.get("status", "queued")
            by_status[status] = by_status.get(status, 0) + 1
        return {
            "worker": data.get("worker", {}),
            "by_status": by_status,
            "queue_length": by_status.get("queued", 0) + by_status.get("retry_queued", 0),
            "pending": by_status.get("queued", 0) + by_status.get("retry_queued", 0),
            "running": by_status.get("running", 0),
            "completed": by_status.get("completed", 0),
            "failed": by_status.get("failed", 0),
            "completed_today": completed_today,
            "failed_today": failed_today,
            "estimated_revenue": self.pipeline_summary()["weighted_forecast"],
        }

    def adapter_registry(self) -> AdapterRegistry:
        return AdapterRegistry(self.load().get("adapters", {}))

    def beta_metrics(self) -> dict[str, Any]:
        data = self.load()
        adapter_registry = self.adapter_registry()
        provider_status = get_provider_registry().status()
        review_summary = content_review_summary()
        local_export_summary = export_summary()
        creator_summary = creator_factory_summary()
        from src.pipeline.pipeline_manager import pipeline_summary as production_pipeline_summary
        from src.automation.automation_manager import automation_summary

        pipeline_metrics = production_pipeline_summary()
        automation_metrics = automation_summary()
        ai_runtime = self.ai_runtime_summary()
        provider_error_count = ai_runtime["failed_jobs"] + int(provider_status.get("provider_errors", 0))
        return {
            "scheduler_status": data.get("scheduler_daemon", {}).get("status", "stopped"),
            "active_adapter": adapter_registry.active_adapter(),
            "api_status": adapter_registry.api_status(),
            "total_articles": len(data.get("article_queue", [])),
            "total_sns_posts": len(data.get("post_queue", [])),
            "total_affiliate_links": len(data.get("affiliate_queue", [])),
            "active_provider": provider_status["active_provider"],
            "current_provider": provider_status["active_provider"],
            "provider_health": provider_status["provider_health"].get(provider_status["active_provider"], {}).get("status", "unknown"),
            "available_providers": ", ".join(provider_status["available_providers"]) or "None",
            "last_provider_call": provider_status["last_provider_call"] or "None",
            "generation_time_ms": ai_runtime["average_runtime_ms"] or provider_status.get("last_generation_time_ms", 0),
            "estimated_token_usage": ai_runtime["average_tokens"] or provider_status["estimated_token_usage"],
            "provider_errors": provider_error_count,
            "pending_reviews": review_summary["pending_reviews"],
            "approved_today": review_summary["approved_today"],
            "rejected_today": review_summary["rejected_today"],
            "revision_requested": review_summary["revision_requested"],
            "publish_ready": review_summary["publish_ready"],
            "risk_warnings": review_summary["risk_warnings"],
            "pending_exports": local_export_summary["pending_exports"],
            "completed_exports": local_export_summary["completed_exports"],
            "failed_exports": local_export_summary["failed_exports"],
            "total_local_packages": local_export_summary["total_local_packages"],
            "active_projects": creator_summary["active_projects"],
            "creator_production_queue": creator_summary["production_queue"],
            "creator_review_queue": creator_summary["review_queue"],
            "creator_export_queue": creator_summary["export_queue"],
            "creator_today_output": creator_summary["today_output"],
            "creator_monthly_output": creator_summary["monthly_output"],
            "creator_average_runtime": creator_summary["average_runtime"],
            "running_pipeline_jobs": pipeline_metrics["running_jobs"],
            "pipeline_completed_today": pipeline_metrics["completed_today"],
            "average_pipeline_time": pipeline_metrics["average_runtime"],
            "approval_waiting": pipeline_metrics["approval_waiting"],
            "export_waiting": pipeline_metrics["export_waiting"],
            "pipeline_failures": pipeline_metrics["failure_count"],
            "automation_running": automation_metrics["running_automations"],
            "today_automation_count": automation_metrics["today_runs"],
            "automation_failures": automation_metrics["failures"],
            "automation_queue": automation_metrics["automation_queue"],
            "next_scheduled_job": automation_metrics["next_scheduled_job"],
        }

    def schedule_runtime_job(
        self,
        job_type: str,
        title: str,
        prompt: str,
        *,
        due_date: str | None = None,
        priority: str = "normal",
        timeout_seconds: int = 60,
        retries: int = 1,
    ) -> dict[str, Any]:
        if job_type not in GEMINI_RUNTIME_JOB_TYPES:
            raise ValueError(f"Unsupported runtime job_type: {job_type}")
        job = self.schedule_job(
            job_type,
            title,
            due_date or date.today().isoformat(),
            priority,
            payload={
                "runtime": "gemini_cli",
                "prompt": prompt,
                "use_workflow": False,
                "timeout_seconds": max(int(timeout_seconds or 60), 1),
                "retries": max(int(retries or 1), 1),
            },
        )
        data = self.load()
        runtime = data.setdefault("ai_runtime", _default_ai_runtime_state())
        runtime.setdefault("prompt_queue", []).insert(0, {
            "job_id": job["job_id"],
            "job_type": job_type,
            "title": title,
            "prompt": prompt,
            "status": "queued",
            "timeout_seconds": max(int(timeout_seconds or 60), 1),
            "retries": max(int(retries or 1), 1),
            "created_at": _now(),
        })
        self.save(data)
        return job

    def update_runtime_queue_status(self, job_id: str, status: str, output_ref: str = "") -> None:
        data = self.load()
        runtime = data.setdefault("ai_runtime", _default_ai_runtime_state())
        for item in runtime.setdefault("prompt_queue", []):
            if item.get("job_id") == job_id:
                item["status"] = status
                item["output_ref"] = output_ref
                item["updated_at"] = _now()
                break
        self.save(data)

    def record_runtime_result(
        self,
        job_id: str,
        job_type: str,
        status: str,
        *,
        duration_ms: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        output_ref: str = "",
        error: str = "",
    ) -> dict[str, Any]:
        data = self.load()
        runtime = data.setdefault("ai_runtime", _default_ai_runtime_state())
        total_tokens = int(input_tokens or 0) + int(output_tokens or 0)
        record = {
            "job_id": job_id,
            "job_type": job_type,
            "status": status,
            "duration_ms": int(duration_ms or 0),
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "total_tokens": total_tokens,
            "estimated_cost_yen": 0,
            "output_ref": output_ref,
            "error": error,
            "created_at": _now(),
        }
        runtime.setdefault("runtime_logs", []).insert(0, record)
        runtime["runtime_logs"] = runtime["runtime_logs"][:300]
        runtime["last_provider_call"] = _now()
        runtime["last_runtime_ms"] = record["duration_ms"]
        runtime["last_tokens"] = total_tokens
        runtime["estimated_cost_yen"] = 0
        self.save(data)
        return record

    def ai_runtime_summary(self) -> dict[str, Any]:
        data = self.load()
        runtime = data.get("ai_runtime", {})
        logs = runtime.get("runtime_logs", [])
        prompt_queue = runtime.get("prompt_queue", [])
        completed = [row for row in logs if row.get("status") == "completed"]
        failed = [row for row in logs if row.get("status") == "failed"]
        avg_runtime = int(sum(int(row.get("duration_ms", 0)) for row in logs) / len(logs)) if logs else 0
        avg_tokens = int(sum(int(row.get("total_tokens", 0)) for row in logs) / len(logs)) if logs else 0
        running = sum(1 for job in data.get("scheduled_jobs", []) if job.get("job_type") in GEMINI_RUNTIME_JOB_TYPES and job.get("status") == "running")
        return {
            "provider": runtime.get("provider", "gemini_cli"),
            "prompt_queue": len([item for item in prompt_queue if item.get("status") in ("queued", "running")]),
            "running_jobs": running,
            "completed_jobs": len(completed),
            "failed_jobs": len(failed),
            "average_runtime_ms": avg_runtime,
            "average_tokens": avg_tokens,
            "average_cost_yen": 0,
            "last_provider_call": runtime.get("last_provider_call", ""),
        }

    def record_daily_kpi(
        self,
        kpi_date: str | None = None,
        revenue: int = 0,
        articles: int = 0,
        sns_posts: int = 0,
        affiliate_clicks: int = 0,
        notes: str = "",
        pv: int = 0,
        ctr: float = 0,
        cv: float = 0,
        seo: int = 0,
        posts: int | None = None,
        roi: int = 0,
        note_articles: int | None = None,
        threads_posts: int | None = None,
    ) -> dict[str, Any]:
        kpi_date = kpi_date or date.today().isoformat()
        data = self.load()
        note_count = int(note_articles if note_articles is not None else int(articles or 0))
        threads_count = int(threads_posts if threads_posts is not None else int(sns_posts or 0))
        row = {
            "date": kpi_date,
            "revenue": int(revenue or 0),
            "articles": int(articles or 0),
            "sns_posts": int(sns_posts or 0),
            "note_articles": note_count,
            "threads_posts": threads_count,
            "affiliate_clicks": int(affiliate_clicks or 0),
            "pv": int(pv or 0),
            "ctr": float(ctr or 0),
            "cv": float(cv or 0),
            "seo": int(seo or 0),
            "posts": int(posts if posts is not None else note_count + threads_count),
            "roi": int(roi or 0),
            "notes": notes,
            "updated_at": _now(),
        }
        data["daily_kpis"] = [k for k in data["daily_kpis"] if k.get("date") != kpi_date]
        data["daily_kpis"].insert(0, row)
        self.save(data)
        return row

    def evaluate_improvement_roi(self, improvement: dict[str, Any]) -> dict[str, Any]:
        data = self.load()
        scored = score_improvement(improvement)
        summary = self.pipeline_summary()
        kpis = data.get("daily_kpis", [])
        recent = kpis[0] if kpis else {}
        evaluation = {
            "evaluation_id": _new_id("beval"),
            "improvement": improvement,
            "score": scored,
            "business_metrics": {
                "pv": int(recent.get("pv", 0) or 0),
                "ctr": float(recent.get("ctr", 0) or 0),
                "cv": float(recent.get("cv", 0) or 0),
                "seo": int(recent.get("seo", 0) or 0),
                "posts": int(recent.get("articles", 0) or 0) + int(recent.get("sns_posts", 0) or 0),
                "revenue": int(recent.get("revenue", 0) or summary.get("earned_revenue", 0)),
                "roi": int(scored.get("roi_score", 0)),
            },
            "decision": "prioritize" if int(scored.get("constitution_priority_score", 0)) >= 30 else "defer",
            "created_at": _now(),
        }
        data.setdefault("constitution_business_evaluations", []).insert(0, evaluation)
        data["constitution_business_evaluations"] = data["constitution_business_evaluations"][:100]
        self.save(data)
        record_improvement(scored)
        return evaluation

    def earnings_forecast(self, days: int = 30) -> dict[str, Any]:
        data = self.load()
        cutoff = date.today() - timedelta(days=days)
        recent = []
        for row in data.get("daily_kpis", []):
            try:
                if date.fromisoformat(row.get("date", "")) >= cutoff:
                    recent.append(row)
            except ValueError:
                continue
        avg_daily = int(sum(int(r.get("revenue", 0)) for r in recent) / len(recent)) if recent else 0
        pipeline = self.pipeline_summary()
        return {
            "window_days": days,
            "avg_daily_revenue": avg_daily,
            "projected_kpi_revenue": avg_daily * days,
            "weighted_pipeline": pipeline["weighted_forecast"],
            "forecast_total": avg_daily * days + pipeline["weighted_forecast"],
        }

    def business_phase1_dashboard(self) -> dict[str, Any]:
        """Local-first dashboard focused on reaching the first AIOS revenue."""
        data = self.load()
        today = date.today().isoformat()
        kpis = data.get("daily_kpis", [])
        today_rows = [row for row in kpis if row.get("date") == today]
        articles = data.get("article_queue", [])
        posts = data.get("post_queue", [])
        threads = [post for post in posts if post.get("platform") == "threads"]
        posting_history = data.get("posting_history", [])
        threads_history = data.get("threads_history", [])
        affiliate_queue = data.get("affiliate_queue", [])

        today_post_count = sum(int(row.get("posts", 0)) for row in today_rows)
        if today_post_count == 0:
            today_post_count = sum(
                1 for row in [*posting_history, *threads_history, *posts]
                if str(row.get("published_at", row.get("posted_at", ""))).startswith(today)
            )

        note_article_ids = {
            str(row.get("article_id", row.get("history_id", "")))
            for row in [*articles, *posting_history]
            if row.get("article_id") or row.get("history_id")
        }
        threads_post_ids = {
            str(row.get("thread_id", row.get("post_id", row.get("history_id", ""))))
            for row in [*threads, *threads_history]
            if row.get("thread_id") or row.get("post_id") or row.get("history_id")
        }
        kpi_note_articles = sum(int(row.get("note_articles", row.get("articles", 0)) or 0) for row in kpis)
        kpi_threads_posts = sum(int(row.get("threads_posts", row.get("sns_posts", 0)) or 0) for row in kpis)
        note_article_count = max(len(note_article_ids), kpi_note_articles)
        threads_post_count = max(len(threads_post_ids), kpi_threads_posts)

        kpi_pv = sum(int(row.get("pv", 0)) for row in kpis)
        article_pv = sum(int(row.get("pv", 0)) for row in articles)
        thread_pv = sum(int(row.get("pv", 0)) for row in threads)
        total_pv = kpi_pv + article_pv + thread_pv

        total_clicks = sum(int(row.get("affiliate_clicks", 0)) for row in kpis)
        total_clicks += sum(int(row.get("clicks", 0)) for row in affiliate_queue)
        ctr_values = [
            float(row.get("ctr", 0) or 0)
            for row in [*kpis, *articles, *threads]
            if float(row.get("ctr", 0) or 0) > 0
        ]
        click_rate = round(total_clicks / max(total_pv, 1), 4) if total_clicks else 0
        avg_ctr = round(sum(ctr_values) / max(len(ctr_values), 1), 4)

        kpi_revenue = sum(int(row.get("revenue", 0)) for row in kpis)
        article_revenue = sum(int(row.get("actual_revenue", 0)) for row in articles)
        affiliate_forecast = sum(int(row.get("estimated_revenue", 0)) for row in affiliate_queue)
        forecast = self.earnings_forecast(days=30)
        pipeline = self.pipeline_summary()
        actual_revenue = kpi_revenue + article_revenue + pipeline["earned_revenue"]
        revenue_prediction = forecast["forecast_total"] + affiliate_forecast

        if actual_revenue > 0:
            first_revenue_progress = 100
        else:
            first_revenue_progress = min(
                90,
                (25 if note_article_count else 0)
                + (25 if threads_post_count else 0)
                + (20 if total_pv > 0 else 0)
                + (10 if total_clicks > 0 or avg_ctr > 0 else 0)
                + (10 if revenue_prediction > 0 else 0),
            )

        return {
            "phase": "Business Engine Phase1",
            "priority": "AIOS initial revenue",
            "local_first": bool(data.get("meta", {}).get("local_first", True)),
            "dry_run": not bool(data.get("meta", {}).get("external_apis_enabled", False)),
            "today_post_count": today_post_count,
            "note_article_count": note_article_count,
            "threads_post_count": threads_post_count,
            "pv": total_pv,
            "clicks": total_clicks,
            "ctr": avg_ctr,
            "click_rate": click_rate,
            "actual_revenue": actual_revenue,
            "revenue_prediction": revenue_prediction,
            "first_revenue_progress_rate": first_revenue_progress,
            "daily_kpis": kpis[:14],
        }

    def record_execution(
        self,
        job_id: str,
        status: str,
        message: str = "",
        output_ref: str = "",
    ) -> dict[str, Any]:
        record = {
            "execution_id": _new_id("exec"),
            "job_id": job_id,
            "status": status,
            "message": message,
            "output_ref": output_ref,
            "created_at": _now(),
        }
        data = self.load()
        data["execution_history"].insert(0, record)
        data["execution_history"] = data["execution_history"][:300]
        self.save(data)
        return record

    def retry_job(self, retry_id: str) -> dict[str, Any] | None:
        data = self.load()
        for retry in data["retry_queue"]:
            if retry.get("retry_id") == retry_id:
                retry["status"] = "queued"
                retry["updated_at"] = _now()
                for job in data["scheduled_jobs"]:
                    if job.get("job_id") == retry.get("job_id"):
                        job["status"] = "retry_queued"
                        job["updated_at"] = _now()
                        break
                self.save(data)
                return retry
        return None

    def _queue_retry(self, data: dict[str, Any], job: dict[str, Any], error: str) -> None:
        existing = next((r for r in data["retry_queue"] if r.get("job_id") == job.get("job_id")), None)
        retry = existing or {
            "retry_id": _new_id("retry"),
            "job_id": job.get("job_id"),
            "job_type": job.get("job_type"),
            "title": job.get("title"),
            "created_at": _now(),
        }
        retry.update({
            "status": "failed",
            "attempts": job.get("attempts", 0),
            "last_error": error or job.get("last_error", ""),
            "updated_at": _now(),
        })
        if existing is None:
            data["retry_queue"].insert(0, retry)


def normalize_job_type(job_type: str) -> str:
    return LEGACY_JOB_TYPE_ALIASES.get(job_type, job_type)
