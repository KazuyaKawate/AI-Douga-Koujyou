from __future__ import annotations

import hashlib
import time
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.approval.approval_queue import (
    approve_content_item,
    create_content_review_item,
    get_content_reviews,
    mark_content_publish_ready,
)
from src.business_engine.manager import BusinessEngineStore
from src.creator_factory.factory_manager import CreatorFactoryManager, PIPELINES
from src.export.export_manager import ExportManager
from src.providers.base_provider import ProviderResult
from src.providers.provider_registry import ProviderRegistry, get_provider_registry
from src.utils.json_store import load_json, save_json_atomic

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = ROOT / "data"

PIPELINE_STATUSES = [
    "created",
    "queued",
    "running",
    "generated",
    "pending_review",
    "approved",
    "publish_ready",
    "exported",
    "completed",
    "failed",
    "cancelled",
]

PIPELINE_TO_CONTENT_TYPE = {
    "note": "note_article",
    "seo_blog": "seo_article",
    "sns": "sns_post",
    "affiliate": "affiliate_description",
    "business_report": "business_report",
}

PIPELINE_TO_BUSINESS_JOB = {
    "note": "note_article",
    "seo_blog": "gemini_seo_article",
    "sns": "sns_post",
    "affiliate": "affiliate_publish",
    "business_report": "gemini_business_report",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class PipelineManager:
    """End-to-end local production pipeline orchestrator."""

    def __init__(
        self,
        data_root: str | Path = DEFAULT_DATA_ROOT,
        *,
        creator: CreatorFactoryManager | None = None,
        business: BusinessEngineStore | None = None,
        export_manager: ExportManager | None = None,
        provider_registry: ProviderRegistry | None = None,
    ) -> None:
        self.data_root = Path(data_root)
        self.pipeline_dir = self.data_root / "pipeline"
        self.generated_dir = self.pipeline_dir / "generated"
        self.pipeline_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.pipeline_dir / "_queue_state.json"
        self.creator = creator or CreatorFactoryManager(self.data_root)
        self.business = business or BusinessEngineStore()
        self.export_manager = export_manager or ExportManager()
        self.provider_registry = provider_registry or get_provider_registry()
        self._last_provider_result: ProviderResult | None = None

    def create_production_job(
        self,
        pipeline: str,
        title: str,
        *,
        project_id: str = "",
        template_id: str = "",
        priority: str = "normal",
    ) -> dict[str, Any]:
        production = self.creator.enqueue_production(
            pipeline,
            title,
            project_id=project_id,
            template_id=template_id,
            priority=priority,
        )
        return self.create_from_production(production["id"])

    def create_from_production(self, production_id: str) -> dict[str, Any]:
        production = self._find_production(production_id)
        if production is None:
            raise ValueError(f"Production item not found: {production_id}")
        pipeline = production.get("pipeline", "")
        if pipeline not in PIPELINES:
            raise ValueError(f"Unsupported pipeline: {pipeline}")

        job_id = _new_id("pipe")
        business_job = self.business.schedule_job(
            PIPELINE_TO_BUSINESS_JOB[pipeline],
            production.get("title", "Production job"),
            priority=production.get("priority", "normal"),
            payload={"pipeline_job_id": job_id, "production_id": production_id, "local_only": True},
        )
        job = {
            "job_id": job_id,
            "project": production.get("project_id", ""),
            "template": production.get("template_id", ""),
            "production_id": production_id,
            "business_job_id": business_job["job_id"],
            "pipeline": pipeline,
            "title": production.get("title", ""),
            "priority": production.get("priority", "normal"),
            "runtime": "local_template",
            "provider": "virtual",
            "provider_model": "virtual-local",
            "generation_time_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "provider_error": "",
            "status": "queued",
            "status_history": [],
            "stage_timestamps": {},
            "approval_result": {},
            "export_result": {},
            "generated_files": [],
            "checksum": "",
            "estimated_runtime_minutes": production.get("estimated_runtime_minutes", PIPELINES[pipeline]["estimated_runtime_minutes"]),
            "estimated_completion": "",
            "last_error": "",
            "created_at": _now(),
            "updated_at": _now(),
            "local_first": True,
            "external_apis_enabled": False,
        }
        self._record_status(job, "created")
        self._record_status(job, "queued")
        self._save_job(job)
        return job

    def execute_selected_template(self, job_id: str, ai_output: str | None = None) -> dict[str, Any]:
        if self.is_paused():
            raise RuntimeError("Pipeline queue is paused.")
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Pipeline job not found: {job_id}")
        if job.get("status") in ("cancelled", "completed"):
            return job
        try:
            self._record_status(job, "running")
            self._last_provider_result = None
            started = time.monotonic()
            content = ai_output or self._generate_local_content(job)
            generation_time_ms = int((time.monotonic() - started) * 1000)
            provider_result = self._last_provider_result
            if provider_result is not None:
                job["runtime"] = provider_result.provider
                job["provider"] = provider_result.provider
                job["provider_model"] = provider_result.model
                job["generation_time_ms"] = int(provider_result.metadata.get("duration_ms") or generation_time_ms)
                job["input_tokens"] = provider_result.input_tokens
                job["output_tokens"] = provider_result.output_tokens
                job["provider_error"] = provider_result.error
                self.business.record_runtime_result(
                    job.get("business_job_id", ""),
                    job.get("pipeline", ""),
                    "completed" if provider_result.ok else "failed",
                    duration_ms=job["generation_time_ms"],
                    input_tokens=provider_result.input_tokens,
                    output_tokens=provider_result.output_tokens,
                    error=provider_result.error,
                )
            generated_path = self._write_generated_content(job, content)
            job["generated_files"] = [str(generated_path)]
            job["checksum"] = checksum_file(generated_path)
            self._record_status(job, "generated")
            review = create_content_review_item(
                title=job.get("title", "Generated content"),
                content=content,
                content_type=PIPELINE_TO_CONTENT_TYPE.get(job.get("pipeline", ""), "business_report"),
                source_job_id=job["job_id"],
            )
            job["approval_result"] = {
                "review_id": review["id"],
                "status": review["status"],
                "risk_flags": review.get("risk_flags", []),
            }
            self._record_status(job, "pending_review")
            self.creator.update_production_status(
                job["production_id"],
                "reviewing",
                approval_status="pending_review",
                output_ref=str(generated_path),
            )
        except Exception as exc:
            job["last_error"] = str(exc)
            self._record_status(job, "failed")
        self._save_job(job)
        return job

    def sync_approval_status(self, job_id: str) -> dict[str, Any]:
        job = self._require_job(job_id)
        review_id = job.get("approval_result", {}).get("review_id", "")
        review = self._get_review(review_id)
        if review is None:
            return job
        job["approval_result"].update({
            "review_id": review_id,
            "status": review.get("status", ""),
            "reviewer_notes": review.get("reviewer_notes", ""),
        })
        status = review.get("status", "")
        if status == "approved" and job.get("status") not in ("approved", "publish_ready", "exported", "completed"):
            self._record_status(job, "approved")
            self.creator.update_production_status(job["production_id"], "approved", approval_status="approved")
        elif status == "publish_ready" and job.get("status") not in ("publish_ready", "exported", "completed"):
            self._record_status(job, "publish_ready")
            self.creator.update_production_status(job["production_id"], "approved", approval_status="approved")
        self._save_job(job)
        return job

    def approve_pipeline_job(self, job_id: str, notes: str = "Approved by local pipeline.") -> dict[str, Any]:
        job = self._require_job(job_id)
        review_id = job.get("approval_result", {}).get("review_id", "")
        if not review_id:
            raise ValueError("Pipeline job has no review item.")
        approve_content_item(review_id, notes)
        mark_content_publish_ready(review_id, "Ready for local export.")
        return self.sync_approval_status(job_id)

    def export_pipeline_job(self, job_id: str) -> dict[str, Any]:
        job = self.sync_approval_status(job_id)
        if job.get("status") != "publish_ready":
            raise ValueError("Pipeline job must be publish_ready before export.")
        review_id = job.get("approval_result", {}).get("review_id", "")
        record = self.export_manager.queue_export(review_id)
        exported = self.export_manager.export_one(record["export_id"])
        if exported is None or exported.get("export_status") != "completed":
            job["export_result"] = exported or {}
            job["last_error"] = (exported or {}).get("last_error", "Export failed.")
            self._record_status(job, "failed")
        else:
            job["export_result"] = exported
            self._record_status(job, "exported")
            self._record_status(job, "completed")
            self.creator.update_production_status(
                job["production_id"],
                "exported",
                approval_status="approved",
                export_status="exported",
                output_ref=exported.get("export_path", ""),
            )
            self.business.update_job_status(job.get("business_job_id", ""), "completed")
        self._save_job(job)
        return job

    def run_until_review(self, job_id: str) -> dict[str, Any]:
        return self.execute_selected_template(job_id)

    def run_full_local(self, job_id: str, *, auto_approve: bool = False) -> dict[str, Any]:
        job = self.execute_selected_template(job_id)
        if auto_approve:
            self.approve_pipeline_job(job_id)
            job = self.export_pipeline_job(job_id)
        return job

    def pause(self) -> dict[str, Any]:
        state = self._queue_state()
        state["paused"] = True
        state["updated_at"] = _now()
        save_json_atomic(self.state_path, state)
        return state

    def resume(self) -> dict[str, Any]:
        state = self._queue_state()
        state["paused"] = False
        state["updated_at"] = _now()
        save_json_atomic(self.state_path, state)
        return state

    def is_paused(self) -> bool:
        return bool(self._queue_state().get("paused", False))

    def cancel(self, job_id: str) -> dict[str, Any]:
        job = self._require_job(job_id)
        self._record_status(job, "cancelled")
        self.creator.update_production_status(job["production_id"], "cancelled")
        self.business.update_job_status(job.get("business_job_id", ""), "failed", "Pipeline job cancelled.")
        self._save_job(job)
        return job

    def retry(self, job_id: str) -> dict[str, Any]:
        job = self._require_job(job_id)
        if job.get("status") not in ("failed", "cancelled"):
            return job
        job["last_error"] = ""
        self._record_status(job, "queued")
        self.creator.update_production_status(job["production_id"], "queued")
        self._save_job(job)
        return job

    def set_priority(self, job_id: str, priority: str) -> dict[str, Any]:
        job = self._require_job(job_id)
        job["priority"] = priority
        job["updated_at"] = _now()
        self._save_job(job)
        return job

    def estimated_completion(self) -> dict[str, Any]:
        queued = [job for job in self.list_jobs() if job.get("status") == "queued"]
        minutes = sum(int(job.get("estimated_runtime_minutes", 0)) for job in queued)
        return {"queue_length": len(queued), "estimated_minutes": minutes}

    def dashboard_summary(self) -> dict[str, Any]:
        jobs = self.list_jobs()
        today = date.today().isoformat()
        completed = [job for job in jobs if job.get("status") == "completed"]
        failed = [job for job in jobs if job.get("status") == "failed"]
        terminal = [job for job in jobs if job.get("status") in ("completed", "failed", "cancelled")]
        avg_runtime = int(sum(_runtime_seconds(job) for job in completed) / len(completed)) if completed else 0
        success_rate = round(len(completed) / len(terminal) * 100, 1) if terminal else 0.0
        return {
            "current_jobs": len([job for job in jobs if job.get("status") not in ("completed", "failed", "cancelled")]),
            "running_jobs": len([job for job in jobs if job.get("status") == "running"]),
            "completed_jobs": len(completed),
            "completed_today": sum(1 for job in completed if str(job.get("updated_at", "")).startswith(today)),
            "approval_waiting": len([job for job in jobs if job.get("status") == "pending_review"]),
            "export_waiting": len([job for job in jobs if job.get("status") == "publish_ready"]),
            "average_runtime": avg_runtime,
            "failure_count": len(failed),
            "success_rate": success_rate,
            "queue_length": len([job for job in jobs if job.get("status") == "queued"]),
            "paused": self.is_paused(),
            "local_first": True,
            "external_apis_enabled": False,
        }

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        data = load_json(self.pipeline_dir / f"{job_id}.json", default=None)
        return data if isinstance(data, dict) else None

    def list_jobs(self, status: str | None = None) -> list[dict[str, Any]]:
        jobs = []
        for path in self.pipeline_dir.glob("pipe_*.json"):
            data = load_json(path, default=None)
            if isinstance(data, dict):
                jobs.append(data)
        if status:
            jobs = [job for job in jobs if job.get("status") == status]
        return sorted(jobs, key=lambda row: row.get("updated_at", row.get("created_at", "")), reverse=True)

    def _queue_state(self) -> dict[str, Any]:
        state = load_json(self.state_path, default=None)
        if not isinstance(state, dict):
            state = {"paused": False, "created_at": _now(), "updated_at": _now()}
            save_json_atomic(self.state_path, state)
        return state

    def _require_job(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Pipeline job not found: {job_id}")
        return job

    def _save_job(self, job: dict[str, Any]) -> Path:
        job["updated_at"] = _now()
        return save_json_atomic(self.pipeline_dir / f"{job['job_id']}.json", job)

    def _record_status(self, job: dict[str, Any], status: str) -> None:
        if status not in PIPELINE_STATUSES:
            status = "failed"
        now = _now()
        job["status"] = status
        job.setdefault("stage_timestamps", {})[status] = now
        job.setdefault("status_history", []).insert(0, {"status": status, "created_at": now})
        job["updated_at"] = now

    def _find_production(self, production_id: str) -> dict[str, Any] | None:
        return next((item for item in self.creator.list_production() if item.get("id") == production_id), None)

    def _generate_local_content(self, job: dict[str, Any]) -> str:
        template = self._template_body(job.get("template", ""))
        prompt = self._build_generation_prompt(job, template)
        result = self.provider_registry.complete(prompt)
        self._last_provider_result = result
        if result.ok and result.content.strip():
            return result.content
        return (
            f"# {job.get('title', 'Untitled')}\n\n"
            f"Pipeline: {job.get('pipeline', '')}\n"
            f"Runtime: {result.provider if result else 'virtual'}\n"
            f"Generated: {_now()}\n\n"
            "## Template\n\n"
            f"{template}\n\n"
            "## Draft\n\n"
            "This local draft was generated without external API calls. "
            "Review, approve, and export it locally before any manual publishing step.\n"
        )

    def _build_generation_prompt(self, job: dict[str, Any], template: str) -> str:
        pipeline = job.get("pipeline", "note")
        content_type = PIPELINE_TO_CONTENT_TYPE.get(pipeline, "business_report")
        return (
            "Generate a local-first draft for AIOS Creator Factory.\n\n"
            f"Title: {job.get('title', 'Untitled')}\n"
            f"Pipeline: {pipeline}\n"
            f"Content type: {content_type}\n"
            f"Template:\n{template}\n\n"
            "Requirements:\n"
            "- Produce review-ready content in Markdown.\n"
            "- Do not claim actual earnings.\n"
            "- Do not include instructions to publish externally.\n"
            "- Keep the draft suitable for local approval and export.\n"
        )

    def _template_body(self, template_id: str) -> str:
        if not template_id:
            return "No template selected."
        for template in self.creator.list_templates():
            if template.get("id") == template_id:
                return template.get("body", "No template body.")
        return "Template not found."

    def _write_generated_content(self, job: dict[str, Any], content: str) -> Path:
        path = self.generated_dir / f"{job['job_id']}.md"
        path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def _get_review(review_id: str) -> dict[str, Any] | None:
        return next((item for item in get_content_reviews() if item.get("id") == review_id), None)


def pipeline_summary(data_root: str | Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    return PipelineManager(data_root).dashboard_summary()


def checksum_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_seconds(job: dict[str, Any]) -> int:
    stamps = job.get("stage_timestamps", {})
    start = stamps.get("running") or stamps.get("created")
    end = stamps.get("completed")
    if not start or not end:
        return 0
    try:
        return int((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds())
    except ValueError:
        return 0
