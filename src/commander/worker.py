from __future__ import annotations

from pathlib import Path
from typing import Any

from src.coding_engine.coding_manager import CodingEngineManager
from src.coding_engine.security_scanner import SecurityScanner
from src.commander.callback_router import CallbackRouter
from src.commander.queue import (
    STATUS_COMPLETED,
    STATUS_DRY_RUN_COMPLETE,
    STATUS_FAILED,
    STATUS_RUNNING,
    CommanderQueue,
)
from src.commander.scheduler import ROIFirstScheduler
from src.commander.self_improvement import CommanderSelfImprovement
from src.utils.config import PROJECT_ROOT


class CommanderWorker:
    def __init__(
        self,
        queue: CommanderQueue | None = None,
        *,
        root: str | Path = PROJECT_ROOT,
        coding_manager: CodingEngineManager | None = None,
    ) -> None:
        self.root = Path(root)
        self.queue = queue or CommanderQueue()
        self.coding_manager = coding_manager or CodingEngineManager(root=self.root)
        self.scheduler = ROIFirstScheduler()
        self.callback_router = CallbackRouter(self.root)
        self.self_improvement = CommanderSelfImprovement()
        self.security = SecurityScanner(self.root)

    def process_next(self, *, dry_run: bool | None = None) -> dict[str, Any]:
        job = self.queue.next_job()
        if not job:
            return {"status": "idle", "message": "No queued commander job."}
        return self.process_job(job, dry_run=dry_run)

    def process_job(self, job: dict[str, Any], *, dry_run: bool | None = None) -> dict[str, Any]:
        dry_run = bool(job.get("dry_run", True) if dry_run is None else dry_run)
        job_id = job.get("job_id", "")
        self.queue.update_job(job_id, status=STATUS_RUNNING, started_at=self._now())
        scheduler = self.scheduler.evaluate(job)
        provider_order = self._provider_order(job)
        provider_health = self.coding_manager.provider_health_probe(timeout_seconds=5)
        state = self.queue.load()
        state["provider_health"] = provider_health
        self.queue.save(state)

        if scheduler.get("decision") == "defer":
            result = self._result(job, "deferred", scheduler, provider_health, {}, {"findings": []})
            result["callback"] = self.callback_router.route(job, result)
            self._finish(job, "deferred", result)
            return result

        target_files = job.get("metadata", {}).get("target_files", [])
        risk_scan = self.security.scan(files=target_files)
        run = self.coding_manager.run_issue(
            job.get("instruction", ""),
            target_files=target_files,
            run_tests=True,
            pytest_args=job.get("metadata", {}).get("pytest_args", ["-q"]),
            apply_approved=False if dry_run else bool(job.get("apply_approved", False)),
            provider_priority=provider_order,
        )
        status = STATUS_COMPLETED if run.get("tests", {}).get("ok") and not risk_scan.get("findings") else STATUS_FAILED
        result = self._result(job, status, scheduler, provider_health, run, risk_scan)
        callback = self.callback_router.route(job, result)
        result["callback"] = callback
        if status == STATUS_FAILED and int(job.get("retry_count", 0)) < int(job.get("max_retries", 2)):
            retry_job = {**job, "retry_count": int(job.get("retry_count", 0)) + 1, "status": "retry_queued", "provider_order": self._rotate(provider_order)}
            retry_updates = {key: value for key, value in retry_job.items() if key != "job_id"}
            self.queue.update_job(job_id, **retry_updates)
            result["retry"] = {"queued": True, "retry_count": retry_job["retry_count"], "provider_order": retry_job["provider_order"]}
            self._record_metrics(job, result)
            return result
        finish_status = STATUS_DRY_RUN_COMPLETE if dry_run and status == STATUS_COMPLETED else status
        self._finish(job, finish_status, result)
        return result

    def _finish(self, job: dict[str, Any], status: str, result: dict[str, Any]) -> None:
        self.queue.finish_job(job.get("job_id", ""), status, result)
        self._record_metrics(job, result)

    def _record_metrics(self, job: dict[str, Any], result: dict[str, Any]) -> None:
        state = self.queue.load()
        self.self_improvement.record(state, job, result)
        self.queue.save(state)

    @staticmethod
    def _provider_order(job: dict[str, Any]) -> list[str]:
        order = job.get("provider_order") or ["claude_cli", "gemini_cli", "openai", "ai_router", "ollama"]
        return [str(item) for item in order]

    @staticmethod
    def _rotate(order: list[str]) -> list[str]:
        return order[1:] + order[:1] if len(order) > 1 else order

    @staticmethod
    def _result(
        job: dict[str, Any],
        status: str,
        scheduler: dict[str, Any],
        provider_health: list[dict[str, Any]],
        run: dict[str, Any],
        risk_scan: dict[str, Any],
    ) -> dict[str, Any]:
        business_score = run.get("business_evaluation", {}).get("score", {}) if run else {}
        return {
            "status": status,
            "job_id": job.get("job_id", ""),
            "engine": job.get("engine", ""),
            "instruction": job.get("instruction", ""),
            "roi_scheduler": scheduler,
            "revenue_gate": scheduler.get("revenue_gate", {}),
            "provider_health": provider_health,
            "coding_run": run,
            "risk_scan": risk_scan,
            "roi": business_score,
            "metrics": {
                "roi": scheduler.get("revenue_gate", {}).get("score", 0),
                "ctr": 0,
                "cvr": 0,
                "profit": business_score.get("estimated_revenue", 0) if isinstance(business_score, dict) else 0,
            },
            "dry_run": bool(job.get("dry_run", True)),
        }

    @staticmethod
    def _now() -> str:
        from datetime import datetime

        return datetime.now().isoformat(timespec="seconds")
